import hashlib
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.storage import get_storage_service, read_upload_limited, validate_pdf_bytes
from app.models.edital import Edital
from app.models.inscricao import Arquivo, Inscricao
from app.models.notificacao import Notificacao
from app.schemas.inscricao import InscricaoDesistirRequest, InscricaoReanalisarRequest
from app.services.academic_service import AcademicIntegrationClient
from app.services.audit_service import log_audit_action
from app.services.workflow_service import STATUS_INSCRICAO_LABEL

logger = logging.getLogger(__name__)

FASES_POS_PRELIMINAR = ("RESULTADO_PRELIMINAR", "EM_RECURSO", "EM_HOMOLOGACAO_FINAL", "ENCERRADO")


async def _ler_e_validar_arquivos(
    edital: Edital, arquivos: Dict[int, UploadFile]
) -> Dict[int, Tuple[UploadFile, bytes]]:
    """Valida que os documentos pertencem ao edital e que todos os arquivos são PDFs válidos."""
    ids_validos = {d.id for d in edital.documentos_exigidos}
    desconhecidos = [doc_id for doc_id in arquivos if doc_id not in ids_validos]
    if desconhecidos:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Um ou mais arquivos foram enviados para documentos que não pertencem a este edital.",
        )
    lidos: Dict[int, Tuple[UploadFile, bytes]] = {}
    for doc_id, upload in arquivos.items():
        content = await read_upload_limited(upload)
        validate_pdf_bytes(content, upload.filename or "documento.pdf")
        lidos[doc_id] = (upload, content)
    return lidos


async def _gravar_arquivos(
    inscricao: Inscricao, edital_id: int, lidos: Dict[int, Tuple[UploadFile, bytes]],
    versoes: Optional[Dict[int, int]] = None,
) -> Tuple[List[Arquivo], List[str]]:
    """Grava os arquivos no storage. Em caso de erro, remove o que já foi gravado e repropaga."""
    storage = get_storage_service()
    gravados: List[str] = []
    registros: List[Arquivo] = []
    try:
        for doc_id, (upload, content) in lidos.items():
            chave = f"editais/{edital_id}/inscricoes/{inscricao.id}/{uuid.uuid4()}.pdf"
            await storage.save_file_stream(chave, content)
            gravados.append(chave)
            registros.append(Arquivo(
                inscricao_id=inscricao.id,
                documento_exigido_id=doc_id,
                chave=chave,
                nome_original=(upload.filename or "documento.pdf")[:255],
                sha256=hashlib.sha256(content).hexdigest(),
                tamanho_bytes=len(content),
                content_type="application/pdf",
                versao=(versoes or {}).get(doc_id, 1),
                ativo=True,
                status_varredura="VALIDADO",
            ))
    except Exception:
        await _remover_arquivos(gravados)
        raise
    return registros, gravados


async def _remover_arquivos(chaves: List[str]) -> None:
    storage = get_storage_service()
    for chave in chaves:
        try:
            await storage.delete(chave)
        except Exception:  # noqa: BLE001 - compensação não deve mascarar o erro original
            logger.exception("Falha ao remover arquivo compensatório %s", chave)


def _motivos_academicos(edital: Edital, vinculo_ativo: Optional[bool], curso: Optional[str], cr: Optional[Decimal]) -> List[str]:
    motivos = []
    if vinculo_ativo is False:
        motivos.append("Discente sem vínculo ativo no sistema acadêmico.")
    cursos_validos = {c.codigo_curso for c in edital.cursos} | {c.nome_curso for c in edital.cursos}
    if not curso or curso not in cursos_validos:
        motivos.append(f"Curso '{curso or 'não informado'}' não é elegível neste edital.")
    if cr is None:
        motivos.append("Coeficiente de rendimento (CR) não informado.")
    elif cr < edital.cr_minimo:
        motivos.append(f"CR ({cr:.2f}) inferior ao mínimo exigido ({edital.cr_minimo:.2f}).")
    return motivos


def _motivos_documentais(edital: Edital, doc_ids_enviados: set) -> List[str]:
    return [
        f"Documento obrigatório ausente: {d.nome}"
        for d in edital.documentos_exigidos
        if d.obrigatorio and d.id not in doc_ids_enviados
    ]


class InscricaoService:

    @staticmethod
    async def submeter_candidatura(
        db: AsyncSession,
        edital_id: int,
        estudante: Dict,
        arquivos_enviados: Dict[int, UploadFile],
        curso_codigo: Optional[str],
        cr_declarado: Optional[Decimal],
        ip_origem: str,
    ) -> Inscricao:
        """Submete candidatura com validação formal automática (INS-02, INS-03, RN-01 a RN-04)."""
        estudante_id = estudante["id"]
        res_edital = await db.execute(
            select(Edital).where(Edital.id == edital_id)
            .options(selectinload(Edital.cursos), selectinload(Edital.documentos_exigidos))
        )
        edital = res_edital.scalar_one_or_none()
        if not edital:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edital não encontrado.")

        now = datetime.now(timezone.utc)
        if edital.status != "ABERTO" or now < edital.data_inicio_inscricao or now > edital.data_fim_inscricao:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="As inscrições deste edital não estão abertas no momento.",
            )

        existente = await db.execute(
            select(Inscricao.id).where(and_(Inscricao.edital_id == edital_id, Inscricao.estudante_id == estudante_id))
        )
        if existente.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Você já possui inscrição neste edital.")

        lidos = await _ler_e_validar_arquivos(edital, arquivos_enviados)

        # Dados acadêmicos: oficiais (integração) ou declarados pelo estudante
        dados_oficiais = await AcademicIntegrationClient.consultar_discente(estudante["email"], estudante.get("matricula"))
        if dados_oficiais is not None:
            vinculo_ativo = bool(dados_oficiais.get("vinculo_ativo"))
            curso_codigo_final = dados_oficiais.get("curso_codigo")
            cr = Decimal(str(dados_oficiais["cr_oficial"])) if dados_oficiais.get("cr_oficial") is not None else None
        else:
            vinculo_ativo = None
            curso_codigo_final = curso_codigo
            cr = cr_declarado

        motivos = _motivos_academicos(edital, vinculo_ativo, curso_codigo_final, cr)
        motivos += _motivos_documentais(edital, set(lidos.keys()))

        if motivos:
            status_inicial = "INDEFERIDA"
        elif dados_oficiais is not None:
            status_inicial = "HOMOLOGADA"
        else:
            status_inicial = "PENDENTE_VALIDACAO_VINCULO"

        nome_curso = next(
            (c.nome_curso for c in edital.cursos if c.codigo_curso == curso_codigo_final),
            (dados_oficiais or {}).get("curso_nome") or curso_codigo_final,
        )

        seq_val = (await db.execute(text("SELECT nextval('seq_protocolo_inscricao')"))).scalar()
        protocolo = f"QUERO-{edital_id:04d}-{seq_val:05d}"

        inscricao = Inscricao(
            protocolo=protocolo,
            edital_id=edital_id,
            estudante_id=estudante_id,
            status=status_inicial,
            motivos_indeferimento=motivos or None,
            vinculo_ativo_congelado=vinculo_ativo,
            curso_congelado=nome_curso,
            cr_congelado=cr,
            data_submissao_original=now,
        )
        db.add(inscricao)
        await db.flush()

        registros, gravados = await _gravar_arquivos(inscricao, edital_id, lidos)
        try:
            db.add_all(registros)
            db.add(Notificacao(
                usuario_id=estudante_id,
                tipo="CONFIRMACAO_INSCRICAO",
                titulo=f"Inscrição recebida - {edital.titulo}"[:200],
                mensagem=(
                    f"Sua inscrição foi registrada sob o protocolo {protocolo}. "
                    f"Situação: {STATUS_INSCRICAO_LABEL.get(status_inicial, status_inicial)}."
                ),
            ))
            await log_audit_action(
                db=db, usuario_id=estudante_id, acao="SUBMETER_INSCRICAO", entidade="inscricoes",
                entidade_id=inscricao.id,
                dados_depois={"protocolo": protocolo, "status": status_inicial, "dados_oficiais": dados_oficiais is not None},
                ip_origem=ip_origem,
            )
            await db.commit()
        except Exception:
            await db.rollback()
            await _remover_arquivos(gravados)
            raise
        return await InscricaoService.get_inscricao_by_id(db, inscricao.id)

    @staticmethod
    async def get_inscricao_by_id(db: AsyncSession, inscricao_id: int) -> Inscricao:
        res = await db.execute(
            select(Inscricao)
            .where(Inscricao.id == inscricao_id)
            .options(
                selectinload(Inscricao.arquivos),
                joinedload(Inscricao.estudante),
                joinedload(Inscricao.edital).selectinload(Edital.cursos),
                joinedload(Inscricao.edital).selectinload(Edital.documentos_exigidos),
                selectinload(Inscricao.avaliacao),
                selectinload(Inscricao.recurso),
            )
            .execution_options(populate_existing=True)
        )
        inscricao = res.scalar_one_or_none()
        if not inscricao:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inscrição não encontrada.")
        return inscricao

    @staticmethod
    async def listar_minhas_inscricoes(db: AsyncSession, estudante_id: int) -> List[Inscricao]:
        res = await db.execute(
            select(Inscricao)
            .where(Inscricao.estudante_id == estudante_id)
            .options(
                selectinload(Inscricao.arquivos),
                joinedload(Inscricao.edital),
                selectinload(Inscricao.avaliacao),
                selectinload(Inscricao.recurso),
            )
            .order_by(Inscricao.id.desc())
        )
        return list(res.scalars().all())

    @staticmethod
    async def listar_inscricoes_edital(db: AsyncSession, edital_id: int, status_filtro: Optional[str]) -> List[Inscricao]:
        query = (
            select(Inscricao)
            .where(Inscricao.edital_id == edital_id)
            .options(
                selectinload(Inscricao.arquivos),
                joinedload(Inscricao.estudante),
                joinedload(Inscricao.edital),
                selectinload(Inscricao.avaliacao),
                selectinload(Inscricao.recurso),
            )
            .order_by(Inscricao.id.asc())
        )
        if status_filtro:
            query = query.where(Inscricao.status == status_filtro)
        res = await db.execute(query)
        return list(res.scalars().all())

    @staticmethod
    async def retificar_inscricao(
        db: AsyncSession,
        inscricao_id: int,
        estudante_id: int,
        arquivos_retificados: Dict[int, UploadFile],
        ip_origem: str,
    ) -> Inscricao:
        """Substitui PDFs no prazo, mantendo protocolo, data original e dados acadêmicos congelados (INS-05)."""
        inscricao = await InscricaoService.get_inscricao_by_id(db, inscricao_id)
        if inscricao.estudante_id != estudante_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissão negada.")
        if inscricao.status == "DESISTENTE":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Inscrições desistentes não podem ser retificadas.")

        edital = inscricao.edital
        now = datetime.now(timezone.utc)
        if edital.status != "ABERTO" or now > edital.data_fim_inscricao:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="O prazo para retificação está encerrado.")

        lidos = await _ler_e_validar_arquivos(edital, arquivos_retificados)

        versoes = {
            doc_id: max([a.versao for a in inscricao.arquivos if a.documento_exigido_id == doc_id] + [0]) + 1
            for doc_id in lidos
        }
        registros, gravados = await _gravar_arquivos(inscricao, edital.id, lidos, versoes)
        try:
            for arq in inscricao.arquivos:
                if arq.documento_exigido_id in lidos and arq.ativo:
                    arq.ativo = False
            db.add_all(registros)
            inscricao.data_ultima_retificacao = now

            # Revalidação completa: documentos ativos + critérios acadêmicos congelados
            docs_ativos = {a.documento_exigido_id for a in inscricao.arquivos if a.ativo} | set(lidos.keys())
            status_anterior = inscricao.status
            if inscricao.status in ("INDEFERIDA", "PENDENTE_VALIDACAO_VINCULO"):
                motivos = _motivos_academicos(
                    edital, inscricao.vinculo_ativo_congelado, inscricao.curso_congelado, inscricao.cr_congelado
                ) + _motivos_documentais(edital, docs_ativos)
                inscricao.motivos_indeferimento = motivos or None
                if motivos:
                    inscricao.status = "INDEFERIDA"
                elif inscricao.vinculo_ativo_congelado:
                    inscricao.status = "HOMOLOGADA"
                else:
                    inscricao.status = "PENDENTE_VALIDACAO_VINCULO"

            await log_audit_action(
                db=db, usuario_id=estudante_id, acao="RETIFICAR_INSCRICAO", entidade="inscricoes",
                entidade_id=inscricao.id,
                dados_antes={"status": status_anterior},
                dados_depois={"status": inscricao.status, "documentos_substituidos": sorted(lidos.keys())},
                ip_origem=ip_origem,
            )
            await db.commit()
        except Exception:
            await db.rollback()
            await _remover_arquivos(gravados)
            raise
        return await InscricaoService.get_inscricao_by_id(db, inscricao.id)

    @staticmethod
    async def desistir_inscricao(
        db: AsyncSession,
        inscricao_id: int,
        estudante_id: int,
        data: InscricaoDesistirRequest,
        ip_origem: str,
    ) -> Inscricao:
        """Registra desistência antes da publicação do resultado preliminar (INS-07)."""
        inscricao = await InscricaoService.get_inscricao_by_id(db, inscricao_id)
        if inscricao.estudante_id != estudante_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissão negada.")
        if inscricao.status == "DESISTENTE":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A desistência já foi registrada.")

        edital = inscricao.edital
        if edital.status in FASES_POS_PRELIMINAR or edital.status == "CANCELADO":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Não é possível desistir após a publicação do resultado preliminar ou em edital cancelado.",
            )

        status_anterior = inscricao.status
        inscricao.status = "DESISTENTE"
        await log_audit_action(
            db=db, usuario_id=estudante_id, acao="DESISTIR_INSCRICAO", entidade="inscricoes",
            entidade_id=inscricao.id,
            dados_antes={"status": status_anterior},
            dados_depois={"status": "DESISTENTE", "motivo": data.motivo},
            ip_origem=ip_origem,
        )
        await db.commit()
        return await InscricaoService.get_inscricao_by_id(db, inscricao.id)

    @staticmethod
    async def reanalisar_inscricao(
        db: AsyncSession,
        inscricao_id: int,
        data: InscricaoReanalisarRequest,
        user_id: int,
        ip_origem: str,
    ) -> Inscricao:
        """Análise manual pela Pró-Reitoria de inscrições pendentes ou indeferidas, antes da avaliação (RN-05)."""
        inscricao = await InscricaoService.get_inscricao_by_id(db, inscricao_id)
        edital = inscricao.edital

        if inscricao.status not in ("INDEFERIDA", "PENDENTE_VALIDACAO_VINCULO"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Somente inscrições pendentes de análise ou indeferidas podem ser reanalisadas.",
            )
        if edital.status not in ("ABERTO", "INSCRICOES_ENCERRADAS"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A análise manual só é permitida antes do início da avaliação de mérito.",
            )

        status_ant = inscricao.status
        if data.deferido:
            inscricao.status = "HOMOLOGADA"
            inscricao.motivos_indeferimento = None
            if inscricao.vinculo_ativo_congelado is None:
                inscricao.vinculo_ativo_congelado = True
        else:
            inscricao.status = "INDEFERIDA"
            motivos = list(inscricao.motivos_indeferimento or [])
            motivos.append(f"Análise da Pró-Reitoria: {data.justificativa}")
            inscricao.motivos_indeferimento = motivos

        inscricao.reanalisada_por = user_id
        inscricao.justificativa_reanalise = data.justificativa

        db.add(Notificacao(
            usuario_id=inscricao.estudante_id,
            tipo="ANALISE_INSCRICAO",
            titulo=f"Inscrição analisada - {edital.titulo}"[:200],
            mensagem=(
                f"Sua inscrição {inscricao.protocolo} foi "
                f"{'homologada' if data.deferido else 'indeferida'} pela Pró-Reitoria. Justificativa: {data.justificativa}"
            ),
        ))
        await log_audit_action(
            db=db, usuario_id=user_id, acao="REANALISAR_INSCRICAO", entidade="inscricoes",
            entidade_id=inscricao.id,
            dados_antes={"status": status_ant},
            dados_depois={"status": inscricao.status, "justificativa": data.justificativa},
            ip_origem=ip_origem,
        )
        await db.commit()
        return await InscricaoService.get_inscricao_by_id(db, inscricao.id)
