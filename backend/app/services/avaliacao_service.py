from decimal import Decimal
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload, joinedload
from fastapi import HTTPException, status

from app.models.edital import Edital, ComissaoEdital
from app.models.inscricao import Inscricao, Arquivo
from app.models.avaliacao import Avaliacao
from app.models.recurso import Recurso
from app.models.user import Usuario
from app.models.notificacao import Notificacao
from app.schemas.avaliacao import AvaliacaoInput
from app.schemas.recurso import RecursoCreate, RecursoJulgamento
from app.schemas.homologacao import ClassificacaoItem, ResultadoPreliminarResponse
from app.services.audit_service import log_audit_action


class AvaliacaoService:

    @staticmethod
    async def listar_inscricoes_para_avaliacao(
        db: AsyncSession,
        edital_id: int,
        avaliador_id: int
    ) -> List[Inscricao]:
        """
        Retorna inscrições HOMOLOGADAS do edital para avaliação pelo membro designado (AVA-01, RN-06, RN-07).
        """
        # 1. Checa designação na comissão (RN-07)
        comissao_check = await db.execute(
            select(ComissaoEdital).where(
                and_(ComissaoEdital.edital_id == edital_id, ComissaoEdital.avaliador_id == avaliador_id)
            )
        )
        if not comissao_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado: o usuário não está formalmente designado na comissão deste edital (RN-07)."
            )

        # 2. Retorna apenas inscrições HOMOLOGADAS (RN-06)
        query = (
            select(Inscricao)
            .where(and_(Inscricao.edital_id == edital_id, Inscricao.status == "HOMOLOGADA"))
            .options(
                selectinload(Inscricao.arquivos),
                selectinload(Inscricao.avaliacao),
                joinedload(Inscricao.estudante)
            )
            .order_by(Inscricao.id.asc())
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def avaliar_inscricao(
        db: AsyncSession,
        inscricao_id: int,
        avaliador_id: int,
        data: AvaliacaoInput,
        ip_origem: str = "127.0.0.1"
    ) -> Avaliacao:
        """
        Lança ou atualiza avaliação com nota, parecer e declaração de não-impedimento (AVA-01, RN-07, RN-08, §7.3).
        """
        # 1. Carrega inscrição
        insc_res = await db.execute(
            select(Inscricao)
            .where(Inscricao.id == inscricao_id)
            .options(joinedload(Inscricao.edital))
        )
        inscricao = insc_res.scalar_one_or_none()
        if not inscricao:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inscrição não encontrada.")

        if inscricao.status != "HOMOLOGADA":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Apenas inscrições com status HOMOLOGADA podem ser avaliadas (RN-06). Status atual: {inscricao.status}."
            )

        edital = inscricao.edital
        if edital.status not in ["INSCRICOES_ENCERRADAS", "EM_AVALIACAO"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Edital não está em período de avaliação de mérito (status atual: {edital.status})."
            )

        # Se o edital ainda estiver em INSCRICOES_ENCERRADAS, transiciona para EM_AVALIACAO (§7.1)
        if edital.status == "INSCRICOES_ENCERRADAS":
            edital.status = "EM_AVALIACAO"

        # 2. Checa se o avaliador está na comissão (RN-07)
        comissao_check = await db.execute(
            select(ComissaoEdital).where(
                and_(ComissaoEdital.edital_id == edital.id, ComissaoEdital.avaliador_id == avaliador_id)
            )
        )
        if not comissao_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Avaliador não está designado para a comissão deste edital (RN-07)."
            )

        # 3. Bloqueio: avaliador não pode ser candidato no mesmo edital (RN-07)
        if inscricao.estudante_id == avaliador_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Conflito de interesse: o avaliador não pode avaliar a própria candidatura (RN-07)."
            )

        # 4. Exige declaração de ausência de impedimento (RN-07)
        if not data.declaracao_sem_impedimento:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="É obrigatório assinalar a declaração de ausência de impedimento/suspeição (RN-07)."
            )

        # 5. Localiza ou cria avaliação existente
        av_res = await db.execute(select(Avaliacao).where(Avaliacao.inscricao_id == inscricao_id))
        avaliacao = av_res.scalar_one_or_none()

        dados_antes = None
        if avaliacao:
            dados_antes = {
                "nota": float(avaliacao.nota_merito) if avaliacao.nota_merito else None,
                "parecer": avaliacao.parecer,
                "status": avaliacao.status
            }
            # Se já estava CONFIRMADA e deseja alterar, exige justificativa de retificação (§7.3)
            if avaliacao.status in ["CONFIRMADA", "RETIFICADA"]:
                if not data.justificativa_retificacao or len(data.justificativa_retificacao.strip()) < 15:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Para alterar avaliação já confirmada, forneça justificativa de retificação com pelo menos 15 caracteres (§7.3)."
                    )
                avaliacao.status = "RETIFICADA"
                avaliacao.justificativa_retificacao = data.justificativa_retificacao
            elif data.confirmar:
                avaliacao.status = "CONFIRMADA"
            else:
                avaliacao.status = "RASCUNHO"

            avaliacao.avaliador_id = avaliador_id
            avaliacao.declaracao_sem_impedimento = True
            avaliacao.nota_merito = data.nota_merito
            avaliacao.parecer = data.parecer
            avaliacao.justificativa = data.justificativa
        else:
            novo_status = "CONFIRMADA" if data.confirmar else "RASCUNHO"
            avaliacao = Avaliacao(
                inscricao_id=inscricao_id,
                avaliador_id=avaliador_id,
                declaracao_sem_impedimento=True,
                nota_merito=data.nota_merito,
                parecer=data.parecer,
                justificativa=data.justificativa,
                status=novo_status,
            )
            db.add(avaliacao)

        await log_audit_action(
            db=db,
            usuario_id=avaliador_id,
            acao="AVALIAR_CANDIDATURA",
            entidade="avaliacoes",
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
        db: AsyncSession,
        edital_id: int,
        user_id: int,
        ip_origem: str = "127.0.0.1"
    ) -> ResultadoPreliminarResponse:
        """
        Calcula classificação preliminar e abre a janela de recurso (AVA-02, RN-09, RN-10, RN-12, §7.1).
        """
        edital_res = await db.execute(select(Edital).where(Edital.id == edital_id))
        edital = edital_res.scalar_one_or_none()
        if not edital:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edital não encontrado.")

        if edital.status != "EM_AVALIACAO":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Resultado preliminar só pode ser publicado com edital em EM_AVALIACAO. Estado atual: {edital.status}."
            )

        # 1. Verifica se todas as inscrições HOMOLOGADAS possuem avaliação Confirmada ou Retificada
        inscricoes_res = await db.execute(
            select(Inscricao)
            .where(and_(Inscricao.edital_id == edital_id, Inscricao.status == "HOMOLOGADA"))
            .options(
                selectinload(Inscricao.avaliacao),
                joinedload(Inscricao.estudante)
            )
        )
        inscricoes = list(inscricoes_res.scalars().all())

        if not inscricoes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Não há inscrições homologadas neste edital para publicação de resultado."
            )

        for insc in inscricoes:
            if not insc.avaliacao or insc.avaliacao.status == "RASCUNHO":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Inscrição {insc.protocolo} ainda possui avaliação pendente ou em Rascunho (AVA-02)."
                )

        # 2. Separa Deferidos e Indeferidos
        deferidos = [i for i in inscricoes if i.avaliacao.parecer == "DEFERIDO"]
        indeferidos = [i for i in inscricoes if i.avaliacao.parecer == "INDEFERIDO"]

        # 3. Ordenação conforme RN-09:
        # Nota decrescente, 1º desempate: maior CR congelado, 2º desempate: menor data_submissao_original
        deferidos.sort(
            key=lambda i: (
                -(i.avaliacao.nota_merito or Decimal("0.00")),
                -(i.cr_congelado or Decimal("0.00")),
                i.data_submissao_original
            )
        )

        # 4. Distribuição das vagas (RN-12): N primeiros = Contemplados, demais = Suplentes
        vagas = edital.vagas
        contemplados_items = []
        suplentes_items = []
        indeferidos_items = []

        for pos, i in enumerate(deferidos, start=1):
            item = ClassificacaoItem(
                posicao=pos,
                inscricao_id=i.id,
                protocolo=i.protocolo,
                nome_estudante=i.estudante.nome,
                matricula=i.estudante.matricula,
                curso=i.curso_congelado or "",
                cr=i.cr_congelado or Decimal("0.00"),
                nota_merito=i.avaliacao.nota_merito or Decimal("0.00"),
                resultado="CONTEMPLADO" if pos <= vagas else "SUPLENTE"
            )
            if pos <= vagas:
                contemplados_items.append(item)
            else:
                suplentes_items.append(item)

        for i in indeferidos:
            item = ClassificacaoItem(
                posicao=0,
                inscricao_id=i.id,
                protocolo=i.protocolo,
                nome_estudante=i.estudante.nome,
                matricula=i.estudante.matricula,
                curso=i.curso_congelado or "",
                cr=i.cr_congelado or Decimal("0.00"),
                nota_merito=i.avaliacao.nota_merito or Decimal("0.00"),
                resultado="INDEFERIDO"
            )
            indeferidos_items.append(item)

        # 5. Transiciona edital para RESULTADO_PRELIMINAR e abre janela de recurso (EM_RECURSO)
        edital.status = "EM_RECURSO"

        # Notifica candidatos
        for insc in inscricoes:
            notif = Notificacao(
                usuario_id=insc.estudante_id,
                tipo="RESULTADO_PRELIMINAR",
                titulo=f"Resultado Preliminar Publicado - {edital.titulo}",
                mensagem=f"O resultado preliminar foi divulgado. A janela de recurso está aberta por {edital.prazo_recurso_horas} horas."
            )
            db.add(notif)

        await log_audit_action(
            db=db,
            usuario_id=user_id,
            acao="PUBLICAR_RESULTADO_PRELIMINAR",
            entidade="editais",
            entidade_id=edital.id,
            dados_depois={"status": "EM_RECURSO", "total_deferidos": len(deferidos), "total_indeferidos": len(indeferidos)},
            ip_origem=ip_origem,
        )

        await db.commit()

        return ResultadoPreliminarResponse(
            edital_id=edital.id,
            titulo=edital.titulo,
            total_homologadas=len(inscricoes),
            total_deferidas=len(deferidos),
            total_indeferidas=len(indeferidos),
            vagas_totais=vagas,
            contemplados=contemplados_items,
            suplentes=suplentes_items,
            indeferidos=indeferidos_items,
        )

    @staticmethod
    async def interpor_recurso(
        db: AsyncSession,
        inscricao_id: int,
        estudante_id: int,
        data: RecursoCreate,
        ip_origem: str = "127.0.0.1"
    ) -> Recurso:
        """
        Interpõe recurso único durante a janela do edital (AVA-03, RN-10).
        """
        insc_res = await db.execute(
            select(Inscricao)
            .where(Inscricao.id == inscricao_id)
            .options(joinedload(Inscricao.edital), selectinload(Inscricao.recurso))
        )
        inscricao = insc_res.scalar_one_or_none()
        if not inscricao:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inscrição não encontrada.")

        if inscricao.estudante_id != estudante_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissão negada.")

        edital = inscricao.edital
        if edital.status != "EM_RECURSO":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Interposição de recurso indisponível. O edital não está na fase recursal (status atual: {edital.status}) (RN-10)."
            )

        # Regra RN-10: Máximo de 1 recurso por candidato
        if inscricao.recurso:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Candidato já possui recurso interposto neste edital (RN-10)."
            )

        novo_recurso = Recurso(
            inscricao_id=inscricao_id,
            texto=data.texto,
            arquivo_anexo_id=data.arquivo_anexo_id,
            status="ABERTO",
        )
        db.add(novo_recurso)

        await log_audit_action(
            db=db,
            usuario_id=estudante_id,
            acao="INTERPOR_RECURSO",
            entidade="recursos",
            entidade_id=inscricao_id,
            dados_depois={"status": "ABERTO"},
            ip_origem=ip_origem,
        )

        await db.commit()
        await db.refresh(novo_recurso)
        return novo_recurso

    @staticmethod
    async def julgar_recurso(
        db: AsyncSession,
        recurso_id: int,
        julgador_id: int,
        data: RecursoJulgamento,
        ip_origem: str = "127.0.0.1"
    ) -> Recurso:
        """
        Julga recurso da seleção preliminar (AVA-04, RN-11).
        Em comissões com 2+ membros, bloqueia (HTTP 403) o autor do parecer original!
        """
        rec_res = await db.execute(
            select(Recurso)
            .where(Recurso.id == recurso_id)
            .options(
                joinedload(Recurso.inscricao).joinedload(Inscricao.edital),
                joinedload(Recurso.inscricao).joinedload(Inscricao.avaliacao)
            )
        )
        recurso = rec_res.scalar_one_or_none()
        if not recurso:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso não encontrado.")

        if recurso.status in ["DEFERIDO", "INDEFERIDO"]:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Recurso já julgado.")

        inscricao = recurso.inscricao
        edital = inscricao.edital

        # Regra RN-11: Se comissão possuir >= 2 membros, bloqueia o autor da avaliação original
        comissao_res = await db.execute(
            select(ComissaoEdital).where(ComissaoEdital.edital_id == edital.id)
        )
        membros_comissao = list(comissao_res.scalars().all())

        if len(membros_comissao) >= 2 and inscricao.avaliacao:
            if inscricao.avaliacao.avaliador_id == julgador_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Comissões com 2 ou mais membros exigem que o recurso seja julgado por avaliador distinto do parecer original (RN-11)."
                )

        now = datetime.now(timezone.utc)
        recurso.status = data.decisao
        recurso.julgado_por = julgador_id
        recurso.justificativa_decisao = data.justificativa_decisao
        recurso.julgado_em = now

        # Se deferido e informada nova nota de mérito, retifica a avaliação (§7.3, AVA-04)
        if data.decisao == "DEFERIDO" and data.nova_nota_merito is not None and inscricao.avaliacao:
            inscricao.avaliacao.nota_merito = data.nova_nota_merito
            inscricao.avaliacao.parecer = "DEFERIDO"
            inscricao.avaliacao.status = "RETIFICADA"
            inscricao.avaliacao.justificativa_retificacao = f"Nota alterada em decorrência de julgamento procedente de recurso: {data.justificativa_decisao}"

        # Notifica o estudante
        notif = Notificacao(
            usuario_id=inscricao.estudante_id,
            tipo="RECURSO_JULGADO",
            titulo=f"Recurso julgado - {edital.titulo}",
            mensagem=f"Seu recurso sob inscrição {inscricao.protocolo} foi julgado como {data.decisao}."
        )
        db.add(notif)

        # Checa se todos os recursos foram julgados; se sim, edital pode transicionar para EM_HOMOLOGACAO_FINAL
        recursos_pendentes_res = await db.execute(
            select(func.count(Recurso.id)).join(Inscricao).where(
                and_(
                    Inscricao.edital_id == edital.id,
                    Recurso.status.in_(["ABERTO", "EM_ANALISE"])
                )
            )
        )
        pendentes = recursos_pendentes_res.scalar() or 0
        if pendentes == 0:
            edital.status = "EM_HOMOLOGACAO_FINAL"

        await log_audit_action(
            db=db,
            usuario_id=julgador_id,
            acao="JULGAR_RECURSO",
            entidade="recursos",
            entidade_id=recurso.id,
            dados_depois={"status": data.decisao, "justificativa": data.justificativa_decisao},
            ip_origem=ip_origem,
        )

        await db.commit()
        await db.refresh(recurso)
        return recurso
