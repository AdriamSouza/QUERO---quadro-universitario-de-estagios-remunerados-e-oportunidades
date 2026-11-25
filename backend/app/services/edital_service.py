from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.edital import ComissaoEdital, Edital, EditalCurso, EditalDocumentoExigido
from app.models.inscricao import Inscricao
from app.models.notificacao import Notificacao
from app.models.user import Usuario
from app.schemas.edital import EditalCancelarRequest, EditalCreate, EditalUpdate
from app.services.audit_service import log_audit_action

# Campos que continuam editáveis após a publicação (apenas texto descritivo - EDT-01)
CAMPOS_EDITAVEIS_APOS_PUBLICACAO = {"titulo", "descricao", "modalidade"}
STATUS_FINAIS = ("ENCERRADO", "CANCELADO")


def _validar_cronograma(edital: Edital) -> None:
    erro = None
    if edital.data_fim_inscricao <= edital.data_inicio_inscricao:
        erro = "O fim das inscrições deve ser posterior ao início."
    elif edital.data_inicio_avaliacao < edital.data_fim_inscricao:
        erro = "O início da avaliação deve ser igual ou posterior ao fim das inscrições."
    elif edital.data_resultado_preliminar < edital.data_inicio_avaliacao:
        erro = "O resultado preliminar deve ser posterior ao início da avaliação."
    elif edital.data_homologacao_final < edital.data_resultado_preliminar:
        erro = "A homologação final deve ser posterior ao resultado preliminar."
    if erro:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=erro)


class EditalService:

    @staticmethod
    async def create_edital(db: AsyncSession, data: EditalCreate, user_id: int, ip_origem: str) -> Edital:
        """Cadastra um novo edital no estado RASCUNHO (EDT-01, EDT-02)."""
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

        codigos = set()
        for curso in data.cursos:
            if curso.codigo_curso in codigos:
                continue
            codigos.add(curso.codigo_curso)
            db.add(EditalCurso(edital_id=novo_edital.id, codigo_curso=curso.codigo_curso, nome_curso=curso.nome_curso))

        for doc in data.documentos_exigidos:
            db.add(EditalDocumentoExigido(
                edital_id=novo_edital.id, nome=doc.nome, descricao=doc.descricao, obrigatorio=doc.obrigatorio,
            ))

        await log_audit_action(
            db=db, usuario_id=user_id, acao="CRIAR_EDITAL_RASCUNHO", entidade="editais",
            entidade_id=novo_edital.id,
            dados_depois={"titulo": novo_edital.titulo, "status": "RASCUNHO"},
            ip_origem=ip_origem,
        )
        await db.commit()
        return await EditalService.get_edital_by_id(db, novo_edital.id)

    @staticmethod
    async def get_edital_by_id(db: AsyncSession, edital_id: int, incluir_rascunho: bool = True) -> Edital:
        result = await db.execute(
            select(Edital)
            .where(Edital.id == edital_id)
            .options(
                selectinload(Edital.cursos),
                selectinload(Edital.documentos_exigidos),
                selectinload(Edital.comissao).joinedload(ComissaoEdital.avaliador),
            )
            .execution_options(populate_existing=True)
        )
        edital = result.scalar_one_or_none()
        if not edital or (edital.status == "RASCUNHO" and not incluir_rascunho):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edital não encontrado.")
        return edital

    @staticmethod
    async def list_editais(
        db: AsyncSession,
        status_filter: Optional[str] = None,
        categoria: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
        somente_abertos: bool = False,
        incluir_rascunho: bool = False,
    ) -> Tuple[List[Edital], int]:
        filtros = []
        if somente_abertos:
            filtros.append(Edital.status == "ABERTO")
        elif status_filter:
            filtros.append(Edital.status == status_filter)
        if not incluir_rascunho:
            filtros.append(Edital.status != "RASCUNHO")
        if categoria:
            filtros.append(Edital.categoria == categoria)
        if search:
            termo = f"%{search.strip()}%"
            filtros.append(or_(Edital.titulo.ilike(termo), Edital.descricao.ilike(termo)))

        total = (await db.execute(select(func.count(Edital.id)).where(*filtros))).scalar() or 0

        result = await db.execute(
            select(Edital)
            .where(*filtros)
            .options(
                selectinload(Edital.cursos),
                selectinload(Edital.documentos_exigidos),
                selectinload(Edital.comissao).joinedload(ComissaoEdital.avaliador),
            )
            .order_by(Edital.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    @staticmethod
    async def update_edital(db: AsyncSession, edital_id: int, data: EditalUpdate, user_id: int, ip_origem: str) -> Edital:
        edital = await EditalService.get_edital_by_id(db, edital_id)
        alteracoes = data.model_dump(exclude_unset=True)

        if edital.status in STATUS_FINAIS:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Editais encerrados ou cancelados não podem ser editados.")
        if edital.status != "RASCUNHO":
            proibidos = set(alteracoes) - CAMPOS_EDITAVEIS_APOS_PUBLICACAO
            if proibidos:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Após a publicação, apenas título, descrição e modalidade podem ser alterados.",
                )

        dados_antes = {k: str(getattr(edital, k)) for k in alteracoes}
        for field, value in alteracoes.items():
            setattr(edital, field, value)
        _validar_cronograma(edital)

        await log_audit_action(
            db=db, usuario_id=user_id, acao="EDITAR_EDITAL", entidade="editais", entidade_id=edital.id,
            dados_antes=dados_antes,
            dados_depois={k: str(v) for k, v in alteracoes.items()},
            ip_origem=ip_origem,
        )
        await db.commit()
        return await EditalService.get_edital_by_id(db, edital_id)

    @staticmethod
    async def publicar_edital(db: AsyncSession, edital_id: int, user_id: int, ip_origem: str) -> Edital:
        """Valida as regras de aceite (EDT-02) e transiciona RASCUNHO -> ABERTO."""
        edital = await EditalService.get_edital_by_id(db, edital_id)
        if edital.status != "RASCUNHO":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Apenas editais em rascunho podem ser publicados.")

        _validar_cronograma(edital)
        if edital.data_fim_inscricao <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="O período de inscrições já terminou. Ajuste o cronograma antes de publicar.",
            )
        if not edital.cursos:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Cadastre ao menos um curso elegível.")
        if not edital.documentos_exigidos:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Cadastre ao menos um documento exigido.")

        edital.status = "ABERTO"
        await log_audit_action(
            db=db, usuario_id=user_id, acao="PUBLICAR_EDITAL", entidade="editais", entidade_id=edital.id,
            dados_antes={"status": "RASCUNHO"}, dados_depois={"status": "ABERTO"}, ip_origem=ip_origem,
        )
        await db.commit()
        return await EditalService.get_edital_by_id(db, edital_id)

    @staticmethod
    async def encerrar_inscricoes(db: AsyncSession, edital_id: int, user_id: int, ip_origem: str) -> Edital:
        """Encerra antecipadamente o período de inscrições (ABERTO -> INSCRICOES_ENCERRADAS)."""
        edital = await EditalService.get_edital_by_id(db, edital_id)
        if edital.status != "ABERTO":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Somente editais com inscrições abertas podem ser encerrados.")
        edital.status = "INSCRICOES_ENCERRADAS"
        await log_audit_action(
            db=db, usuario_id=user_id, acao="ENCERRAR_INSCRICOES", entidade="editais", entidade_id=edital.id,
            dados_antes={"status": "ABERTO"}, dados_depois={"status": "INSCRICOES_ENCERRADAS"}, ip_origem=ip_origem,
        )
        await db.commit()
        return await EditalService.get_edital_by_id(db, edital_id)

    @staticmethod
    async def cancelar_edital(db: AsyncSession, edital_id: int, data: EditalCancelarRequest, user_id: int, ip_origem: str) -> Edital:
        edital = await EditalService.get_edital_by_id(db, edital_id)
        if edital.status in STATUS_FINAIS:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este edital já está encerrado ou cancelado.")

        status_anterior = edital.status
        edital.status = "CANCELADO"
        edital.justificativa_cancelamento = data.justificativa

        inscritos = await db.execute(
            select(Inscricao.estudante_id).where(
                and_(Inscricao.edital_id == edital_id, Inscricao.status != "DESISTENTE")
            )
        )
        for (estudante_id,) in inscritos.all():
            db.add(Notificacao(
                usuario_id=estudante_id,
                tipo="EDITAL_CANCELADO",
                titulo=f"Edital cancelado - {edital.titulo}"[:200],
                mensagem=f"O edital foi cancelado pela Pró-Reitoria. Justificativa: {data.justificativa}",
            ))

        await log_audit_action(
            db=db, usuario_id=user_id, acao="CANCELAR_EDITAL", entidade="editais", entidade_id=edital.id,
            dados_antes={"status": status_anterior},
            dados_depois={"status": "CANCELADO", "justificativa": data.justificativa},
            ip_origem=ip_origem,
        )
        await db.commit()
        return await EditalService.get_edital_by_id(db, edital_id)

    @staticmethod
    async def designar_comissao(
        db: AsyncSession, edital_id: int, avaliadores_ids: List[int], user_id: int, ip_origem: str
    ) -> List[ComissaoEdital]:
        """Designa a comissão avaliadora (EDT-04, RN-07)."""
        edital = await EditalService.get_edital_by_id(db, edital_id)
        if edital.status in STATUS_FINAIS:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Não é possível alterar a comissão de um edital encerrado.")

        ids = sorted(set(avaliadores_ids))
        usuarios = (await db.execute(select(Usuario).where(Usuario.id.in_(ids)))).scalars().all()
        encontrados: Dict[int, Usuario] = {u.id: u for u in usuarios}
        invalidos = [i for i in ids if i not in encontrados or not encontrados[i].ativo or encontrados[i].perfil not in ("AVALIADOR", "PRO_REITOR")]
        if invalidos:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Somente usuários ativos com perfil de avaliador podem compor a comissão.",
            )

        impedidos = (await db.execute(
            select(Inscricao.estudante_id).where(and_(Inscricao.edital_id == edital_id, Inscricao.estudante_id.in_(ids)))
        )).scalars().all()
        if impedidos:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Candidatos inscritos no edital não podem compor a comissão avaliadora.",
            )

        ja_designados = {m.avaliador_id for m in edital.comissao}
        for av_id in ids:
            if av_id not in ja_designados:
                db.add(ComissaoEdital(edital_id=edital_id, avaliador_id=av_id, designado_por=user_id))

        await log_audit_action(
            db=db, usuario_id=user_id, acao="DESIGNAR_COMISSAO", entidade="editais", entidade_id=edital_id,
            dados_depois={"avaliadores_designados": ids}, ip_origem=ip_origem,
        )
        await db.commit()
        return await EditalService.listar_comissao(db, edital_id)

    @staticmethod
    async def remover_membro_comissao(db: AsyncSession, edital_id: int, avaliador_id: int, user_id: int, ip_origem: str) -> List[ComissaoEdital]:
        edital = await EditalService.get_edital_by_id(db, edital_id)
        if edital.status not in ("RASCUNHO", "ABERTO", "INSCRICOES_ENCERRADAS"):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A comissão não pode ser alterada após o início da avaliação.")
        membro = next((m for m in edital.comissao if m.avaliador_id == avaliador_id), None)
        if not membro:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avaliador não pertence à comissão.")
        await db.delete(membro)
        await log_audit_action(
            db=db, usuario_id=user_id, acao="REMOVER_MEMBRO_COMISSAO", entidade="editais", entidade_id=edital_id,
            dados_antes={"avaliador_id": avaliador_id}, ip_origem=ip_origem,
        )
        await db.commit()
        return await EditalService.listar_comissao(db, edital_id)

    @staticmethod
    async def listar_comissao(db: AsyncSession, edital_id: int) -> List[ComissaoEdital]:
        result = await db.execute(
            select(ComissaoEdital).where(ComissaoEdital.edital_id == edital_id).options(joinedload(ComissaoEdital.avaliador))
        )
        return list(result.scalars().all())

    @staticmethod
    async def usuario_na_comissao(db: AsyncSession, edital_id: int, usuario_id: int) -> bool:
        res = await db.execute(
            select(ComissaoEdital.id).where(
                and_(ComissaoEdital.edital_id == edital_id, ComissaoEdital.avaliador_id == usuario_id)
            )
        )
        return res.scalar_one_or_none() is not None
