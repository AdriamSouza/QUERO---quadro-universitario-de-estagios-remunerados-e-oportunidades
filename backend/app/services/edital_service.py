from decimal import Decimal
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload, joinedload
from fastapi import HTTPException, status

from app.models.edital import Edital, EditalCurso, EditalDocumentoExigido, ComissaoEdital
from app.models.user import Usuario
from app.models.inscricao import Inscricao
from app.schemas.edital import EditalCreate, EditalUpdate, EditalCancelarRequest
from app.services.audit_service import log_audit_action


class EditalService:

    @staticmethod
    async def create_edital(
        db: AsyncSession,
        data: EditalCreate,
        user_id: int,
        ip_origem: str = "127.0.0.1"
    ) -> Edital:
        """
        Cadastra um novo edital estruturado no estado inicial RASCUNHO (v5.0 EDT-01, EDT-02).
        """
        novo_edital = Edital(
            titulo=data.titulo,
            descricao=data.descricao,
            categoria=data.categoria,
            modalidade=data.modalidade,
            valor_bolsa=data.valor_bolsa,
            carga_horaria_semanal=data.carga_horaria_semanal,
            vagas=data.vagas,
            cr_minimo=data.cr_minimo,
            prazo_recurso_horas=data.prazo_recurso_horas,
            criterios_pontuacao=data.criterios_pontuacao,
            criterios_desempate=data.criterios_desempate,
            status="RASCUNHO",
            data_inicio_inscricao=data.data_inicio_inscricao,
            data_fim_inscricao=data.data_fim_inscricao,
            data_inicio_avaliacao=data.data_inicio_avaliacao,
            data_resultado_preliminar=data.data_resultado_preliminar,
            data_homologacao_final=data.data_homologacao_final,
            criado_por=user_id,
        )
        db.add(novo_edital)
        await db.flush()

        # Cursos autorizados
        for curso in data.cursos:
            edital_curso = EditalCurso(
                edital_id=novo_edital.id,
                codigo_curso=curso.codigo_curso,
                nome_curso=curso.nome_curso
            )
            db.add(edital_curso)

        # Documentos obrigatórios
        for doc in data.documentos_exigidos:
            doc_obj = EditalDocumentoExigido(
                edital_id=novo_edital.id,
                nome=doc.nome,
                descricao=doc.descricao,
                obrigatorio=doc.obrigatorio,
            )
            db.add(doc_obj)

        await db.flush()

        # Auditoria (RN-14)
        await log_audit_action(
            db=db,
            usuario_id=user_id,
            acao="CRIAR_EDITAL_RASCUNHO",
            entidade="editais",
            entidade_id=novo_edital.id,
            dados_depois={"titulo": novo_edital.titulo, "status": novo_edital.status},
            ip_origem=ip_origem,
        )

        await db.commit()
        return await EditalService.get_edital_by_id(db, novo_edital.id)

    @staticmethod
    async def get_edital_by_id(db: AsyncSession, edital_id: int) -> Edital:
        query = (
            select(Edital)
            .where(Edital.id == edital_id)
            .options(
                selectinload(Edital.cursos),
                selectinload(Edital.documentos_exigidos),
                selectinload(Edital.comissao).joinedload(ComissaoEdital.avaliador),
            )
        )
        result = await db.execute(query)
        edital = result.scalar_one_or_none()
        if not edital:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Edital com ID {edital_id} não encontrado."
            )
        return edital

    @staticmethod
    async def list_editais(
        db: AsyncSession,
        status_filter: Optional[str] = None,
        categoria: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
        somente_abertos: bool = False
    ) -> (List[Edital], int):
        query = select(Edital).options(
            selectinload(Edital.cursos),
            selectinload(Edital.documentos_exigidos),
            selectinload(Edital.comissao).joinedload(ComissaoEdital.avaliador),
        )

        if somente_abertos:
            query = query.where(Edital.status == "ABERTO")
        elif status_filter:
            query = query.where(Edital.status == status_filter)

        if categoria:
            query = query.where(Edital.categoria == categoria)

        if search:
            query = query.where(
                or_(
                    Edital.titulo.ilike(f"%{search}%"),
                    Edital.descricao.ilike(f"%{search}%")
                )
            )

        count_query = select(func.count(Edital.id))
        if somente_abertos:
            count_query = count_query.where(Edital.status == "ABERTO")
        elif status_filter:
            count_query = count_query.where(Edital.status == status_filter)
        if categoria:
            count_query = count_query.where(Edital.categoria == categoria)

        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(Edital.id.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all()), total

    @staticmethod
    async def update_edital(
        db: AsyncSession,
        edital_id: int,
        data: EditalUpdate,
        user_id: int,
        ip_origem: str = "127.0.0.1"
    ) -> Edital:
        edital = await EditalService.get_edital_by_id(db, edital_id)

        # Se já estiver publicado (não Rascunho), só permite alteração de texto descritivo (EDT-01, RN-14)
        if edital.status != "RASCUNHO":
            if any([
                data.valor_bolsa is not None,
                data.vagas is not None,
                data.cr_minimo is not None,
                data.data_inicio_inscricao is not None,
                data.data_fim_inscricao is not None
            ]):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Edital publicado só permite edição de texto descritivo (EDT-01, RN-14)."
                )

        dados_antes = {"titulo": edital.titulo, "descricao": edital.descricao, "status": edital.status}

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(edital, field, value)

        await log_audit_action(
            db=db,
            usuario_id=user_id,
            acao="EDITAR_EDITAL",
            entidade="editais",
            entidade_id=edital.id,
            dados_antes=dados_antes,
            dados_depois={"titulo": edital.titulo, "descricao": edital.descricao, "status": edital.status},
            ip_origem=ip_origem,
        )

        await db.commit()
        return await EditalService.get_edital_by_id(db, edital_id)

    @staticmethod
    async def publicar_edital(
        db: AsyncSession,
        edital_id: int,
        user_id: int,
        ip_origem: str = "127.0.0.1"
    ) -> Edital:
        """
        Valida regras de aceite EDT-02 e transiciona RASCUNHO -> ABERTO (v5.0 §7.1).
        """
        edital = await EditalService.get_edital_by_id(db, edital_id)
        if edital.status != "RASCUNHO":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Apenas editais em RASCUNHO podem ser publicados. Estado atual: {edital.status}."
            )

        # Critério de Aceite EDT-02:
        # fim_inscricao <= inicio_inscricao, inicio_avaliacao < fim_inscricao,
        # resultado_preliminar < inicio_avaliacao ou sem ao menos um curso e um documento
        if edital.data_fim_inscricao <= edital.data_inicio_inscricao:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="data_fim_inscricao deve ser posterior a data_inicio_inscricao (EDT-02)."
            )
        if edital.data_inicio_avaliacao < edital.data_fim_inscricao:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="data_inicio_avaliacao deve ser igual ou posterior a data_fim_inscricao (EDT-02)."
            )
        if edital.data_resultado_preliminar < edital.data_inicio_avaliacao:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="data_resultado_preliminar deve ser posterior a data_inicio_avaliacao (EDT-02)."
            )
        if len(edital.cursos) < 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Edital deve possuir pelo menos um curso autorizado para publicação (EDT-02)."
            )
        if len(edital.documentos_exigidos) < 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Edital deve possuir pelo menos um documento obrigatório para publicação (EDT-02)."
            )

        edital.status = "ABERTO"

        await log_audit_action(
            db=db,
            usuario_id=user_id,
            acao="PUBLICAR_EDITAL",
            entidade="editais",
            entidade_id=edital.id,
            dados_antes={"status": "RASCUNHO"},
            dados_depois={"status": "ABERTO"},
            ip_origem=ip_origem,
        )

        await db.commit()
        return await EditalService.get_edital_by_id(db, edital_id)

    @staticmethod
    async def cancelar_edital(
        db: AsyncSession,
        edital_id: int,
        data: EditalCancelarRequest,
        user_id: int,
        ip_origem: str = "127.0.0.1"
    ) -> Edital:
        edital = await EditalService.get_edital_by_id(db, edital_id)
        if edital.status == "ENCERRADO":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Editais no estado ENCERRADO não podem ser cancelados."
            )

        status_anterior = edital.status
        edital.status = "CANCELADO"
        edital.justificativa_cancelamento = data.justificativa

        await log_audit_action(
            db=db,
            usuario_id=user_id,
            acao="CANCELAR_EDITAL",
            entidade="editais",
            entidade_id=edital.id,
            dados_antes={"status": status_anterior},
            dados_depois={"status": "CANCELADO", "justificativa": data.justificativa},
            ip_origem=ip_origem,
        )

        await db.commit()
        return await EditalService.get_edital_by_id(db, edital_id)

    @staticmethod
    async def designar_comissao(
        db: AsyncSession,
        edital_id: int,
        avaliadores_ids: List[int],
        user_id: int,
        ip_origem: str = "127.0.0.1"
    ) -> List[ComissaoEdital]:
        """
        Designa comissão avaliadora do edital (EDT-04, RN-07).
        Bloqueia tecnicamente que um usuário seja avaliador e candidato no mesmo edital.
        """
        edital = await EditalService.get_edital_by_id(db, edital_id)

        # Verifica se algum dos avaliadores é candidato no edital
        candidato_check = await db.execute(
            select(Inscricao.estudante_id).where(
                and_(
                    Inscricao.edital_id == edital_id,
                    Inscricao.estudante_id.in_(avaliadores_ids)
                )
            )
        )
        candidatos_impedidos = candidato_check.scalars().all()
        if candidatos_impedidos:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Usuário(s) com ID {candidatos_impedidos} possui(em) inscrição neste edital e não pode(m) ser designados para a comissão (RN-07)."
            )

        for av_id in avaliadores_ids:
            # Checa se já está designado
            existente = await db.execute(
                select(ComissaoEdital).where(
                    and_(
                        ComissaoEdital.edital_id == edital_id,
                        ComissaoEdital.avaliador_id == av_id
                    )
                )
            )
            if not existente.scalar_one_or_none():
                membro = ComissaoEdital(
                    edital_id=edital_id,
                    avaliador_id=av_id,
                    designado_por=user_id
                )
                db.add(membro)

        await log_audit_action(
            db=db,
            usuario_id=user_id,
            acao="DESIGNAR_COMISSAO",
            entidade="editais",
            entidade_id=edital_id,
            dados_depois={"avaliadores_designados": avaliadores_ids},
            ip_origem=ip_origem,
        )

        await db.commit()
        query = select(ComissaoEdital).where(ComissaoEdital.edital_id == edital_id).options(joinedload(ComissaoEdital.avaliador))
        result = await db.execute(query)
        return list(result.scalars().all())
