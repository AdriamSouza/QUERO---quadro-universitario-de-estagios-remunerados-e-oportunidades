import os
import uuid
import hashlib
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.orm import selectinload, joinedload
from fastapi import HTTPException, status, UploadFile

from app.models.inscricao import Inscricao, Arquivo
from app.models.edital import Edital, EditalCurso, EditalDocumentoExigido, ComissaoEdital
from app.models.user import Usuario
from app.models.notificacao import Notificacao
from app.schemas.inscricao import InscricaoReanalisarRequest, InscricaoDesistirRequest
from app.core.storage import get_storage_service, MAGIC_PDF_BYTES
from app.core.config import settings
from app.services.academic_service import AcademicIntegrationClient
from app.services.audit_service import log_audit_action


class InscricaoService:

    @staticmethod
    async def submeter_candidatura(
        db: AsyncSession,
        edital_id: int,
        estudante_id: int,
        estudante_email: str,
        arquivos_enviados: Dict[int, UploadFile],
        ip_origem: str = "127.0.0.1"
    ) -> Inscricao:
        """
        Submete uma nova candidatura com upload em streaming e validação formal automática (INS-02, INS-03, RN-01 a RN-05).
        """
        # 1. Carrega edital
        query_edital = (
            select(Edital)
            .where(Edital.id == edital_id)
            .options(
                selectinload(Edital.cursos),
                selectinload(Edital.documentos_exigidos)
            )
        )
        res_edital = await db.execute(query_edital)
        edital = res_edital.scalar_one_or_none()
        if not edital:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edital não encontrado.")

        # Valida status do edital e janela de submissão (RN-03)
        if edital.status != "ABERTO":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Inscrições indisponíveis: o edital não está aberto (status: {edital.status})."
            )

        now = datetime.now(timezone.utc)
        if now < edital.data_inicio_inscricao or now > edital.data_fim_inscricao:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Fora do prazo regulamentar de inscrições do edital (RN-03)."
            )

        # 2. Regra RN-01: No máximo uma inscrição por edital
        query_insc = select(Inscricao).where(
            and_(Inscricao.edital_id == edital_id, Inscricao.estudante_id == estudante_id)
        )
        res_insc = await db.execute(query_insc)
        if res_insc.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Candidato já possui inscrição registrada para este edital (RN-01)."
            )

        # 3. Geração de Protocolo Atômico Sequencial
        try:
            seq_res = await db.execute(text("SELECT nextval('seq_protocolo_inscricao')"))
            seq_val = seq_res.scalar()
        except Exception:
            seq_val = int(now.timestamp())
        protocolo = f"QUERO-{edital_id:04d}-{seq_val:05d}"

        # 4. Validação de documentos obrigatórios (RN-04)
        docs_obrigatorios = [d for d in edital.documentos_exigidos if d.obrigatorio]
        motivos_indeferimento = []

        for doc_obrig in docs_obrigatorios:
            if doc_obrig.id not in arquivos_enviados:
                motivos_indeferimento.append(f"Documento obrigatório ausente: {doc_obrig.nome}")

        # 5. Consulta e congelamento acadêmico (RN-02, INT-01)
        api_disponivel = True
        try:
            dados_acad = await AcademicIntegrationClient.consultar_discente(estudante_email)
            if not dados_acad:
                api_disponivel = False
        except Exception:
            api_disponivel = False

        vinculo_ativo = None
        curso_aluno = None
        cr_aluno = None

        if api_disponivel and dados_acad:
            vinculo_ativo = dados_acad.get("vinculo_ativo", False)
            curso_aluno = dados_acad.get("curso_nome") or dados_acad.get("curso_codigo")
            cr_aluno = Decimal(str(dados_acad.get("cr_oficial", 0.0)))

            # Valida elegibilidade acadêmica
            if not vinculo_ativo:
                motivos_indeferimento.append("Discente sem vínculo ativo no Sistema Acadêmico (RN-02).")

            cursos_permitidos = [c.codigo_curso for c in edital.cursos]
            aluno_codigo = dados_acad.get("curso_codigo")
            if aluno_codigo and aluno_codigo not in cursos_permitidos:
                motivos_indeferimento.append(f"Curso '{curso_aluno}' não contemplado nas vagas do edital (RN-02).")

            if cr_aluno < edital.cr_minimo:
                motivos_indeferimento.append(f"CR acumulado ({cr_aluno}) inferior ao CR mínimo exigido ({edital.cr_minimo}) (RN-02).")

        # Determina status inicial conforme máquina de estados §7.2
        if not api_disponivel:
            status_inicial = "PENDENTE_VALIDACAO_VINCULO"
        elif len(motivos_indeferimento) > 0:
            status_inicial = "INDEFERIDA"
        else:
            status_inicial = "HOMOLOGADA"

        # 6. Salva Inscrição
        inscricao = Inscricao(
            protocolo=protocolo,
            edital_id=edital_id,
            estudante_id=estudante_id,
            status=status_inicial,
            motivos_indeferimento=motivos_indeferimento if motivos_indeferimento else None,
            vinculo_ativo_congelado=vinculo_ativo,
            curso_congelado=curso_aluno or "Não informado",
            cr_congelado=cr_aluno or Decimal("0.00"),
            data_submissao_original=now,
        )
        db.add(inscricao)
        await db.flush()

        # 7. Salva Arquivos via ArmazenamentoDisco com validação %PDF- e SHA-256
        storage = get_storage_service()
        salvos = []

        for doc_id, upload_file in arquivos_enviados.items():
            content = await upload_file.read()
            if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Arquivo '{upload_file.filename}' excede o tamanho máximo de 10 MB (RN-04)."
                )
            if not content.startswith(MAGIC_PDF_BYTES):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Arquivo '{upload_file.filename}' não é um PDF válido com assinatura %PDF- (RN-04)."
                )

            sha256 = hashlib.sha256(content).hexdigest()
            chave_logica = f"editais/{edital_id}/inscricoes/{inscricao.id}/{uuid.uuid4()}.pdf"
            await storage.save_file_stream(chave_logica, content)
            salvos.append(chave_logica)

            arquivo = Arquivo(
                inscricao_id=inscricao.id,
                documento_exigido_id=doc_id,
                chave=chave_logica,
                nome_original=upload_file.filename or "documento.pdf",
                sha256=sha256,
                tamanho_bytes=len(content),
                content_type="application/pdf",
                versao=1,
                ativo=True,
                status_varredura="VALIDADO",
            )
            db.add(arquivo)

        # 8. Notificação e Auditoria
        notificacao = Notificacao(
            usuario_id=estudante_id,
            tipo="CONFIRMACAO_INSCRICAO",
            titulo=f"Inscrição recebida com sucesso - {edital.titulo}",
            mensagem=f"Sua candidatura no edital foi recebida sob protocolo {protocolo}. Status: {status_inicial}."
        )
        db.add(notificacao)

        await log_audit_action(
            db=db,
            usuario_id=estudante_id,
            acao="SUBMETER_INSCRICAO",
            entidade="inscricoes",
            entidade_id=inscricao.id,
            dados_depois={"protocolo": protocolo, "status": status_inicial},
            ip_origem=ip_origem,
        )

        await db.commit()
        return await InscricaoService.get_inscricao_by_id(db, inscricao.id)

    @staticmethod
    async def get_inscricao_by_id(db: AsyncSession, inscricao_id: int) -> Inscricao:
        query = (
            select(Inscricao)
            .where(Inscricao.id == inscricao_id)
            .options(
                selectinload(Inscricao.arquivos),
                joinedload(Inscricao.estudante),
                joinedload(Inscricao.edital)
            )
        )
        res = await db.execute(query)
        inscricao = res.scalar_one_or_none()
        if not inscricao:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inscrição não encontrada.")
        return inscricao

    @staticmethod
    async def listar_minhas_inscricoes(db: AsyncSession, estudante_id: int) -> List[Inscricao]:
        query = (
            select(Inscricao)
            .where(Inscricao.estudante_id == estudante_id)
            .options(
                selectinload(Inscricao.arquivos),
                joinedload(Inscricao.edital)
            )
            .order_by(Inscricao.id.desc())
        )
        res = await db.execute(query)
        return list(res.scalars().all())

    @staticmethod
    async def retificar_inscricao(
        db: AsyncSession,
        inscricao_id: int,
        estudante_id: int,
        arquivos_retificados: Dict[int, UploadFile],
        ip_origem: str = "127.0.0.1"
    ) -> Inscricao:
        """
        Substitui PDFs durante o prazo regulamentar mantendo protocolo, data original e CR congelado (INS-05, RN-04, RN-09).
        """
        inscricao = await InscricaoService.get_inscricao_by_id(db, inscricao_id)
        if inscricao.estudante_id != estudante_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissão negada.")

        edital = inscricao.edital
        if edital.status != "ABERTO":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Edital não está mais aberto para retificações.")

        now = datetime.now(timezone.utc)
        if now > edital.data_fim_inscricao:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Prazo de inscrição encerrado.")

        storage = get_storage_service()

        for doc_id, upload_file in arquivos_retificados.items():
            content = await upload_file.read()
            if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Arquivo '{upload_file.filename}' excede 10 MB.")
            if not content.startswith(MAGIC_PDF_BYTES):
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Arquivo '{upload_file.filename}' não é PDF válido.")

            # Desativa arquivo anterior para este documento exigido
            for arq in inscricao.arquivos:
                if arq.documento_exigido_id == doc_id and arq.ativo:
                    arq.ativo = False

            nova_versao = max([a.versao for a in inscricao.arquivos if a.documento_exigido_id == doc_id] + [0]) + 1
            chave_logica = f"editais/{edital.id}/inscricoes/{inscricao.id}/{uuid.uuid4()}.pdf"
            await storage.save_file_stream(chave_logica, content)

            novo_arq = Arquivo(
                inscricao_id=inscricao.id,
                documento_exigido_id=doc_id,
                chave=chave_logica,
                nome_original=upload_file.filename or "retificado.pdf",
                sha256=hashlib.sha256(content).hexdigest(),
                tamanho_bytes=len(content),
                content_type="application/pdf",
                versao=nova_versao,
                ativo=True,
                status_varredura="VALIDADO",
            )
            db.add(novo_arq)

        inscricao.data_ultima_retificacao = now

        # Se os motivos de indeferimento anteriores eram puramente documentais, podemos reavaliar
        # Se os critérios acadêmicos eram ok, homologa
        if inscricao.status == "INDEFERIDA":
            if inscricao.vinculo_ativo_congelado and inscricao.cr_congelado >= edital.cr_minimo:
                inscricao.status = "HOMOLOGADA"
                inscricao.motivos_indeferimento = None

        await log_audit_action(
            db=db,
            usuario_id=estudante_id,
            acao="RETIFICAR_INSCRICAO",
            entidade="inscricoes",
            entidade_id=inscricao.id,
            dados_depois={"data_retificacao": str(now), "status": inscricao.status},
            ip_origem=ip_origem,
        )

        await db.commit()
        return await InscricaoService.get_inscricao_by_id(db, inscricao.id)

    @staticmethod
    async def desistir_inscricao(
        db: AsyncSession,
        inscricao_id: int,
        estudante_id: int,
        data: InscricaoDesistirRequest,
        ip_origem: str = "127.0.0.1"
    ) -> Inscricao:
        """
        Marca inscrição como Desistente antes do resultado preliminar (INS-07).
        """
        inscricao = await InscricaoService.get_inscricao_by_id(db, inscricao_id)
        if inscricao.estudante_id != estudante_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissão negada.")

        edital = inscricao.edital
        if edital.status in ["RESULTADO_PRELIMINAR", "EM_RECURSO", "EM_HOMOLOGACAO_FINAL", "ENCERRADO"]:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Desistência não permitida após a publicação do resultado preliminar (INS-07).")

        status_anterior = inscricao.status
        inscricao.status = "DESISTENTE"

        await log_audit_action(
            db=db,
            usuario_id=estudante_id,
            acao="DESISTIR_INSCRICAO",
            entidade="inscricoes",
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
        ip_origem: str = "127.0.0.1"
    ) -> Inscricao:
        """
        Reanálise manual de indeferimento pelo Pró-Reitor até o início da avaliação (RN-05).
        """
        inscricao = await InscricaoService.get_inscricao_by_id(db, inscricao_id)
        edital = inscricao.edital

        now = datetime.now(timezone.utc)
        if now >= edital.data_inicio_avaliacao or edital.status in ["EM_AVALIACAO", "RESULTADO_PRELIMINAR", "ENCERRADO"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Reanálise manual só pode ser realizada antes do início da avaliação de mérito (RN-05)."
            )

        status_ant = inscricao.status
        if data.deferido:
            inscricao.status = "HOMOLOGADA"
            inscricao.motivos_indeferimento = None
        else:
            inscricao.status = "INDEFERIDA"

        inscricao.reanalisada_por = user_id
        inscricao.justificativa_reanalise = data.justificativa

        await log_audit_action(
            db=db,
            usuario_id=user_id,
            acao="REANALISAR_INSCRICAO",
            entidade="inscricoes",
            entidade_id=inscricao.id,
            dados_antes={"status": status_ant},
            dados_depois={"status": inscricao.status, "justificativa": data.justificativa},
            ip_origem=ip_origem,
        )

        await db.commit()
        return await InscricaoService.get_inscricao_by_id(db, inscricao.id)
