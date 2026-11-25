import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import get_storage_service
from app.models.edital import Edital
from app.models.homologacao import AtaHomologacao
from app.models.inscricao import Arquivo, Inscricao
from app.models.notificacao import Notificacao
from app.models.recurso import Recurso
from app.models.user import Usuario
from app.schemas.homologacao import DevolverAjustesRequest, HomologacaoFinalRequest
from app.services.audit_service import log_audit_action
from app.services.avaliacao_service import _carregar_inscricoes_homologadas
from app.services.report_service import ReportService
from app.services.workflow_service import classificar, janela_recurso_aberta


class HomologacaoService:

    @staticmethod
    async def homologar_final(
        db: AsyncSession, edital_id: int, pro_reitor_id: int, data: HomologacaoFinalRequest, ip_origem: str
    ) -> AtaHomologacao:
        """Homologa o resultado final, gera ata (PDF) e lista (CSV) e encerra o edital (HOM-01, HOM-02, RN-13)."""
        edital = (await db.execute(select(Edital).where(Edital.id == edital_id))).scalar_one_or_none()
        if not edital:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edital não encontrado.")
        if edital.status not in ("EM_HOMOLOGACAO_FINAL", "EM_RECURSO"):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="O edital não está apto para a homologação final.")
        if janela_recurso_aberta(edital):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="O prazo de recursos ainda está aberto. A homologação só pode ocorrer após o seu encerramento.",
            )

        pendentes = (await db.execute(
            select(func.count(Recurso.id)).join(Inscricao).where(
                and_(Inscricao.edital_id == edital_id, Recurso.status.in_(["ABERTO", "EM_ANALISE"]))
            )
        )).scalar() or 0
        if pendentes:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Existem recursos pendentes de julgamento.")

        inscricoes = await _carregar_inscricoes_homologadas(db, edital_id)
        classificacao = classificar(edital, inscricoes)
        titulares, suplentes = classificacao["contemplados"], classificacao["suplentes"]

        pr_user = (await db.execute(select(Usuario).where(Usuario.id == pro_reitor_id))).scalar_one_or_none()
        pr_nome = pr_user.nome if pr_user else f"Usuário #{pro_reitor_id}"
        now = datetime.now(timezone.utc)
        despacho = (data.justificativa or "").strip() or "Homologo o resultado final do processo seletivo, nos termos do edital."

        pdf_bytes = ReportService.gerar_ata_homologacao_pdf(
            edital_id=edital.id, edital_titulo=edital.titulo, homologador_nome=pr_nome,
            data_homologacao=now, titulares=titulares, suplentes=suplentes, despacho=despacho,
        )
        # BOM para que o Excel reconheça a acentuação
        csv_bytes = ("﻿" + ReportService.gerar_folha_csv(
            edital_id=edital.id, edital_titulo=edital.titulo, valor_bolsa=edital.valor_bolsa,
            carga_horaria=edital.carga_horaria_semanal, titulares=titulares, suplentes=suplentes,
        )).encode("utf-8")

        storage = get_storage_service()
        chave_pdf = f"editais/{edital.id}/atas/ata_homologacao_{uuid.uuid4()}.pdf"
        chave_csv = f"editais/{edital.id}/atas/lista_aprovados_{uuid.uuid4()}.csv"
        await storage.save_file_stream(chave_pdf, pdf_bytes)
        try:
            await storage.save_file_stream(chave_csv, csv_bytes)
        except Exception:
            await storage.delete(chave_pdf)
            raise

        try:
            arq_pdf = Arquivo(
                chave=chave_pdf, nome_original=f"ata_homologacao_edital_{edital.id}.pdf",
                sha256=hashlib.sha256(pdf_bytes).hexdigest(), tamanho_bytes=len(pdf_bytes),
                content_type="application/pdf", versao=1, ativo=True, status_varredura="VALIDADO",
            )
            arq_csv = Arquivo(
                chave=chave_csv, nome_original=f"lista_aprovados_edital_{edital.id}.csv",
                sha256=hashlib.sha256(csv_bytes).hexdigest(), tamanho_bytes=len(csv_bytes),
                content_type="text/csv", versao=1, ativo=True, status_varredura="VALIDADO",
            )
            db.add_all([arq_pdf, arq_csv])
            await db.flush()

            ata = AtaHomologacao(
                edital_id=edital.id, homologado_por=pro_reitor_id,
                arquivo_pdf_id=arq_pdf.id, arquivo_csv_id=arq_csv.id,
                eh_retificacao=False, homologado_em=now,
            )
            db.add(ata)
            status_anterior = edital.status
            edital.status = "ENCERRADO"
            await db.flush()

            contemplados_ids = {t["inscricao_id"] for t in titulares}
            suplentes_ids = {s["inscricao_id"] for s in suplentes}
            for insc in inscricoes:
                if insc.id in contemplados_ids:
                    situacao = "Parabéns! Você foi contemplado(a) neste processo seletivo."
                elif insc.id in suplentes_ids:
                    situacao = "Você foi classificado(a) no cadastro de reserva (suplência)."
                else:
                    situacao = "Você não foi classificado(a) neste processo seletivo."
                db.add(Notificacao(
                    usuario_id=insc.estudante_id,
                    tipo="RESULTADO_FINAL",
                    titulo=f"Resultado final homologado - {edital.titulo}"[:200],
                    mensagem=f"{situacao} A ata de homologação está disponível na página do edital.",
                ))

            await log_audit_action(
                db=db, usuario_id=pro_reitor_id, acao="HOMOLOGAR_RESULTADO_FINAL", entidade="editais", entidade_id=edital.id,
                dados_antes={"status": status_anterior},
                dados_depois={"status": "ENCERRADO", "ata_id": ata.id, "titulares": len(titulares), "suplentes": len(suplentes)},
                ip_origem=ip_origem,
            )
            await db.commit()
        except Exception:
            await db.rollback()
            await storage.delete(chave_pdf)
            await storage.delete(chave_csv)
            raise

        await db.refresh(ata)
        return ata

    @staticmethod
    async def devolver_ajustes(
        db: AsyncSession, edital_id: int, pro_reitor_id: int, data: DevolverAjustesRequest, ip_origem: str
    ) -> Edital:
        """Devolve o edital de EM_HOMOLOGACAO_FINAL para EM_AVALIACAO, com justificativa (HOM-01)."""
        edital = (await db.execute(select(Edital).where(Edital.id == edital_id))).scalar_one_or_none()
        if not edital:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edital não encontrado.")
        if edital.status != "EM_HOMOLOGACAO_FINAL":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Somente editais aguardando homologação final podem ser devolvidos para ajustes.",
            )

        edital.status = "EM_AVALIACAO"
        edital.data_publicacao_preliminar = None
        await log_audit_action(
            db=db, usuario_id=pro_reitor_id, acao="DEVOLVER_EDITAL_AJUSTES", entidade="editais", entidade_id=edital.id,
            dados_antes={"status": "EM_HOMOLOGACAO_FINAL"},
            dados_depois={"status": "EM_AVALIACAO", "justificativa": data.justificativa},
            ip_origem=ip_origem,
        )
        await db.commit()
        from app.services.edital_service import EditalService
        return await EditalService.get_edital_by_id(db, edital_id)
