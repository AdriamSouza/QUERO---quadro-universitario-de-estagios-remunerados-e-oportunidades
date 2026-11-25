from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.avaliacao import Avaliacao
from app.models.edital import ComissaoEdital, Edital
from app.models.inscricao import Arquivo, Inscricao
from app.models.notificacao import Notificacao
from app.models.recurso import Recurso
from app.schemas.avaliacao import AvaliacaoInput
from app.schemas.homologacao import ClassificacaoItem, ResultadoPreliminarResponse
from app.schemas.recurso import RecursoCreate, RecursoJulgamento
from app.services.audit_service import log_audit_action
from app.services.edital_service import EditalService
from app.services.workflow_service import classificar, fim_janela_recurso, janela_recurso_aberta

FASES_RESULTADO_PUBLICO = ("EM_RECURSO", "EM_HOMOLOGACAO_FINAL", "ENCERRADO")


async def _exigir_comissao(db: AsyncSession, edital_id: int, usuario_id: int) -> None:
    if not await EditalService.usuario_na_comissao(db, edital_id, usuario_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não está designado(a) para a comissão avaliadora deste edital.",
        )


async def _carregar_inscricoes_homologadas(db: AsyncSession, edital_id: int) -> List[Inscricao]:
    res = await db.execute(
        select(Inscricao)
        .where(and_(Inscricao.edital_id == edital_id, Inscricao.status == "HOMOLOGADA"))
        .options(selectinload(Inscricao.avaliacao), joinedload(Inscricao.estudante))
        .execution_options(populate_existing=True)
    )
    return list(res.scalars().all())


def _montar_resultado(edital: Edital, inscricoes: List[Inscricao], ocultar_matricula: bool) -> ResultadoPreliminarResponse:
    classificacao = classificar(edital, inscricoes)

    def _itens(chave: str) -> List[ClassificacaoItem]:
        itens = []
        for item in classificacao[chave]:
            if ocultar_matricula:
                item = {**item, "matricula": None}
            itens.append(ClassificacaoItem(**item))
        return itens

    return ResultadoPreliminarResponse(
        edital_id=edital.id,
        titulo=edital.titulo,
        status_edital=edital.status,
        publicado_em=edital.data_publicacao_preliminar,
        prazo_recurso_ate=fim_janela_recurso(edital),
        total_homologadas=len(inscricoes),
        total_deferidas=classificacao["total_deferidos"],
        total_indeferidas=classificacao["total_indeferidos"],
        vagas_totais=edital.vagas,
        contemplados=_itens("contemplados"),
        suplentes=_itens("suplentes"),
        indeferidos=_itens("indeferidos"),
    )


class AvaliacaoService:

    @staticmethod
    async def listar_inscricoes_para_avaliacao(db: AsyncSession, edital_id: int, avaliador_id: int) -> List[Inscricao]:
        """Inscrições HOMOLOGADAS do edital para o membro designado da comissão (AVA-01, RN-06, RN-07)."""
        await _exigir_comissao(db, edital_id, avaliador_id)
        res = await db.execute(
            select(Inscricao)
            .where(and_(Inscricao.edital_id == edital_id, Inscricao.status == "HOMOLOGADA"))
            .options(
                selectinload(Inscricao.arquivos),
                selectinload(Inscricao.avaliacao),
                selectinload(Inscricao.recurso),
                joinedload(Inscricao.estudante),
                joinedload(Inscricao.edital),
            )
            .order_by(Inscricao.id.asc())
        )
        return list(res.scalars().all())

    @staticmethod
    async def avaliar_inscricao(
        db: AsyncSession, inscricao_id: int, avaliador_id: int, data: AvaliacaoInput, ip_origem: str
    ) -> Avaliacao:
        """Lança ou atualiza avaliação com nota, parecer e declaração de não impedimento (AVA-01, RN-07, RN-08)."""
        inscricao = (await db.execute(
            select(Inscricao).where(Inscricao.id == inscricao_id).options(joinedload(Inscricao.edital))
        )).scalar_one_or_none()
        if not inscricao:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inscrição não encontrada.")
        if inscricao.status != "HOMOLOGADA":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Apenas inscrições homologadas podem ser avaliadas.")

        edital = inscricao.edital
        if edital.status not in ("INSCRICOES_ENCERRADAS", "EM_AVALIACAO"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="O edital não está em fase de avaliação de mérito.",
            )

        await _exigir_comissao(db, edital.id, avaliador_id)
        if inscricao.estudante_id == avaliador_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conflito de interesse: não é permitido avaliar a própria candidatura.")
        if not data.declaracao_sem_impedimento:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="É obrigatório declarar a ausência de impedimento ou suspeição.",
            )

        if edital.status == "INSCRICOES_ENCERRADAS":
            edital.status = "EM_AVALIACAO"

        avaliacao = (await db.execute(select(Avaliacao).where(Avaliacao.inscricao_id == inscricao_id))).scalar_one_or_none()
        dados_antes = None
        if avaliacao:
            dados_antes = {
                "nota": float(avaliacao.nota_merito) if avaliacao.nota_merito is not None else None,
                "parecer": avaliacao.parecer,
                "status": avaliacao.status,
                "avaliador_id": avaliacao.avaliador_id,
            }
            if avaliacao.status in ("CONFIRMADA", "RETIFICADA"):
                if avaliacao.avaliador_id != avaliador_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Esta avaliação já foi confirmada por outro membro da comissão.",
                    )
                if not data.justificativa_retificacao or len(data.justificativa_retificacao.strip()) < 15:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Para alterar uma avaliação confirmada, informe a justificativa da retificação (mínimo de 15 caracteres).",
                    )
                avaliacao.status = "RETIFICADA"
                avaliacao.justificativa_retificacao = data.justificativa_retificacao
            else:
                avaliacao.status = "CONFIRMADA" if data.confirmar else "RASCUNHO"
            avaliacao.avaliador_id = avaliador_id
            avaliacao.declaracao_sem_impedimento = True
            avaliacao.nota_merito = data.nota_merito
            avaliacao.parecer = data.parecer
            avaliacao.justificativa = data.justificativa
        else:
            avaliacao = Avaliacao(
                inscricao_id=inscricao_id,
                avaliador_id=avaliador_id,
                declaracao_sem_impedimento=True,
                nota_merito=data.nota_merito,
                parecer=data.parecer,
                justificativa=data.justificativa,
                status="CONFIRMADA" if data.confirmar else "RASCUNHO",
            )
            db.add(avaliacao)

        await log_audit_action(
            db=db, usuario_id=avaliador_id, acao="AVALIAR_CANDIDATURA", entidade="avaliacoes",
            entidade_id=inscricao_id,
            dados_antes=dados_antes,
            dados_depois={"nota": float(data.nota_merito), "parecer": data.parecer, "status": avaliacao.status},
            ip_origem=ip_origem,
        )
        await db.commit()
        await db.refresh(avaliacao)
        return avaliacao

    @staticmethod
    async def publicar_resultado_preliminar(
        db: AsyncSession, edital_id: int, user: dict, ip_origem: str
    ) -> ResultadoPreliminarResponse:
        """Calcula a classificação, publica o resultado preliminar e abre a janela de recurso (AVA-02, RN-09, RN-10, RN-12)."""
        edital = (await db.execute(select(Edital).where(Edital.id == edital_id))).scalar_one_or_none()
        if not edital:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edital não encontrado.")
        if "PRO_REITOR" not in user["perfis"]:
            await _exigir_comissao(db, edital_id, user["id"])
        if edital.status != "EM_AVALIACAO":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="O resultado preliminar só pode ser publicado com o edital em fase de avaliação.",
            )

        inscricoes = await _carregar_inscricoes_homologadas(db, edital_id)
        if not inscricoes:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Não há inscrições homologadas neste edital.")
        pendentes = [i.protocolo for i in inscricoes if not i.avaliacao or i.avaliacao.status == "RASCUNHO"]
        if pendentes:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ainda há {len(pendentes)} avaliação(ões) pendente(s) ou em rascunho (ex.: {pendentes[0]}).",
            )

        edital.status = "EM_RECURSO"
        edital.data_publicacao_preliminar = datetime.now(timezone.utc)

        for insc in inscricoes:
            db.add(Notificacao(
                usuario_id=insc.estudante_id,
                tipo="RESULTADO_PRELIMINAR",
                titulo=f"Resultado preliminar publicado - {edital.titulo}"[:200],
                mensagem=f"O resultado preliminar foi divulgado. O prazo para recurso é de {edital.prazo_recurso_horas} horas.",
            ))

        resultado = _montar_resultado(edital, inscricoes, ocultar_matricula=False)
        await log_audit_action(
            db=db, usuario_id=user["id"], acao="PUBLICAR_RESULTADO_PRELIMINAR", entidade="editais", entidade_id=edital.id,
            dados_depois={"status": "EM_RECURSO", "total_deferidos": resultado.total_deferidas, "total_indeferidos": resultado.total_indeferidas},
            ip_origem=ip_origem,
        )
        await db.commit()
        return resultado

    @staticmethod
    async def consultar_resultado(db: AsyncSession, edital_id: int, ocultar_matricula: bool) -> ResultadoPreliminarResponse:
        edital = (await db.execute(select(Edital).where(Edital.id == edital_id))).scalar_one_or_none()
        if not edital:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edital não encontrado.")
        if edital.status not in FASES_RESULTADO_PUBLICO:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="O resultado deste edital ainda não foi publicado.")
        inscricoes = await _carregar_inscricoes_homologadas(db, edital_id)
        return _montar_resultado(edital, inscricoes, ocultar_matricula)

    @staticmethod
    async def interpor_recurso(
        db: AsyncSession, inscricao_id: int, estudante_id: int, data: RecursoCreate, ip_origem: str
    ) -> Recurso:
        """Interpõe recurso único dentro da janela do edital (AVA-03, RN-10)."""
        inscricao = (await db.execute(
            select(Inscricao).where(Inscricao.id == inscricao_id)
            .options(joinedload(Inscricao.edital), selectinload(Inscricao.recurso))
        )).scalar_one_or_none()
        if not inscricao:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inscrição não encontrada.")
        if inscricao.estudante_id != estudante_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissão negada.")
        if inscricao.status != "HOMOLOGADA":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Somente candidaturas avaliadas podem receber recurso.")

        edital = inscricao.edital
        if not janela_recurso_aberta(edital):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="O prazo para interposição de recurso não está aberto.")
        if inscricao.recurso:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Você já interpôs recurso neste edital.")

        if data.arquivo_anexo_id is not None:
            anexo = (await db.execute(select(Arquivo).where(Arquivo.id == data.arquivo_anexo_id))).scalar_one_or_none()
            if not anexo or anexo.inscricao_id != inscricao.id:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="O anexo informado não pertence a esta inscrição.")

        recurso = Recurso(inscricao_id=inscricao_id, texto=data.texto, arquivo_anexo_id=data.arquivo_anexo_id, status="ABERTO")
        db.add(recurso)
        await db.flush()
        await log_audit_action(
            db=db, usuario_id=estudante_id, acao="INTERPOR_RECURSO", entidade="recursos", entidade_id=recurso.id,
            dados_depois={"status": "ABERTO", "inscricao_id": inscricao_id}, ip_origem=ip_origem,
        )
        await db.commit()
        await db.refresh(recurso)
        return recurso

    @staticmethod
    async def listar_recursos(db: AsyncSession, edital_id: int, user: dict) -> List[Recurso]:
        if "PRO_REITOR" not in user["perfis"]:
            await _exigir_comissao(db, edital_id, user["id"])
        res = await db.execute(
            select(Recurso)
            .join(Inscricao, Inscricao.id == Recurso.inscricao_id)
            .where(Inscricao.edital_id == edital_id)
            .options(
                joinedload(Recurso.inscricao).joinedload(Inscricao.estudante),
                joinedload(Recurso.inscricao).selectinload(Inscricao.avaliacao),
            )
            .order_by(Recurso.id.asc())
        )
        return list(res.scalars().unique().all())

    @staticmethod
    async def julgar_recurso(
        db: AsyncSession, recurso_id: int, julgador: dict, data: RecursoJulgamento, ip_origem: str
    ) -> Recurso:
        """Julga recurso (AVA-04, RN-11): em comissões com 2+ membros, o autor do parecer original não pode julgar."""
        julgador_id = julgador["id"]
        recurso = (await db.execute(
            select(Recurso).where(Recurso.id == recurso_id).options(
                joinedload(Recurso.inscricao).joinedload(Inscricao.edital),
                joinedload(Recurso.inscricao).selectinload(Inscricao.avaliacao),
                joinedload(Recurso.inscricao).joinedload(Inscricao.estudante),
            )
        )).scalar_one_or_none()
        if not recurso:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso não encontrado.")
        if recurso.status in ("DEFERIDO", "INDEFERIDO"):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este recurso já foi julgado.")

        inscricao = recurso.inscricao
        edital = inscricao.edital
        if edital.status not in ("EM_RECURSO", "EM_HOMOLOGACAO_FINAL"):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="O edital não está em fase recursal.")

        membros = (await db.execute(select(ComissaoEdital.avaliador_id).where(ComissaoEdital.edital_id == edital.id))).scalars().all()
        if julgador_id not in membros and "PRO_REITOR" not in julgador["perfis"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não está designado(a) para a comissão deste edital.")
        if len(membros) >= 2 and inscricao.avaliacao and inscricao.avaliacao.avaliador_id == julgador_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="O recurso deve ser julgado por membro diferente do autor da avaliação original.",
            )

        recurso.status = data.decisao
        recurso.julgado_por = julgador_id
        recurso.justificativa_decisao = data.justificativa_decisao
        recurso.julgado_em = datetime.now(timezone.utc)

        nota_anterior = inscricao.avaliacao.nota_merito if inscricao.avaliacao else None
        if data.decisao == "DEFERIDO" and data.nova_nota_merito is not None and inscricao.avaliacao:
            inscricao.avaliacao.nota_merito = data.nova_nota_merito
            inscricao.avaliacao.parecer = "DEFERIDO"
            inscricao.avaliacao.status = "RETIFICADA"
            inscricao.avaliacao.justificativa_retificacao = f"Nota alterada em razão de recurso deferido: {data.justificativa_decisao}"

        db.add(Notificacao(
            usuario_id=inscricao.estudante_id,
            tipo="RECURSO_JULGADO",
            titulo=f"Recurso julgado - {edital.titulo}"[:200],
            mensagem=f"Seu recurso referente à inscrição {inscricao.protocolo} foi {'deferido' if data.decisao == 'DEFERIDO' else 'indeferido'}.",
        ))

        await log_audit_action(
            db=db, usuario_id=julgador_id, acao="JULGAR_RECURSO", entidade="recursos", entidade_id=recurso.id,
            dados_antes={"status": "ABERTO", "nota": float(nota_anterior) if nota_anterior is not None else None},
            dados_depois={
                "status": data.decisao,
                "justificativa": data.justificativa_decisao,
                "nova_nota": float(data.nova_nota_merito) if data.nova_nota_merito is not None else None,
            },
            ip_origem=ip_origem,
        )

        # Encerrada a janela e sem pendências, o edital segue para a homologação final
        await db.flush()
        pendentes = (await db.execute(
            select(func.count(Recurso.id)).join(Inscricao).where(
                and_(Inscricao.edital_id == edital.id, Recurso.status.in_(["ABERTO", "EM_ANALISE"]))
            )
        )).scalar() or 0
        if pendentes == 0 and edital.status == "EM_RECURSO" and not janela_recurso_aberta(edital):
            edital.status = "EM_HOMOLOGACAO_FINAL"

        await db.commit()
        return (await db.execute(
            select(Recurso).where(Recurso.id == recurso.id).options(
                joinedload(Recurso.inscricao).joinedload(Inscricao.estudante),
                joinedload(Recurso.inscricao).selectinload(Inscricao.avaliacao),
            ).execution_options(populate_existing=True)
        )).scalar_one()
