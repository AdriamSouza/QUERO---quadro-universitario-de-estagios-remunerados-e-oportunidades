import uuid
import hashlib
from decimal import Decimal
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload, joinedload
from fastapi import HTTPException, status

from app.models.edital import Edital
from app.models.inscricao import Inscricao, Arquivo
from app.models.avaliacao import Avaliacao
from app.models.recurso import Recurso
from app.models.homologacao import AtaHomologacao
from app.models.user import Usuario
from app.models.notificacao import Notificacao
from app.schemas.homologacao import HomologacaoFinalRequest, DevolverAjustesRequest
from app.services.report_service import ReportService
from app.services.audit_service import log_audit_action
from app.core.storage import get_storage_service


class HomologacaoService:

    @staticmethod
    async def homologar_final(
        db: AsyncSession,
        edital_id: int,
        pro_reitor_id: int,
        data: HomologacaoFinalRequest,
        ip_origem: str = "127.0.0.1"
    ) -> AtaHomologacao:
        """
        Homologa o resultado final, oficializa contemplados/suplentes, gera PDF/CSV da ata e encerra o edital (HOM-01, HOM-02, RN-13, §7.1).
        """
        edital_res = await db.execute(
            select(Edital).where(Edital.id == edital_id)
        )
        edital = edital_res.scalar_one_or_none()
        if not edital:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edital não encontrado.")

        if edital.status not in ["EM_HOMOLOGACAO_FINAL", "EM_RECURSO"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Edital não está apto para homologação final. Status atual: {edital.status}."
            )

        # 1. Verifica se existem recursos pendentes de julgamento (HOM-01)
        recursos_pendentes_res = await db.execute(
            select(func.count(Recurso.id)).join(Inscricao).where(
                and_(
                    Inscricao.edital_id == edital_id,
                    Recurso.status.in_(["ABERTO", "EM_ANALISE"])
                )
            )
        )
        if (recursos_pendentes_res.scalar() or 0) > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Existem recursos pendentes de julgamento pela comissão. A homologação final está bloqueada (HOM-01)."
            )

        # 2. Carrega inscrições homologadas com avaliações
        insc_res = await db.execute(
            select(Inscricao)
            .where(and_(Inscricao.edital_id == edital_id, Inscricao.status == "HOMOLOGADA"))
            .options(
                selectinload(Inscricao.avaliacao),
                joinedload(Inscricao.estudante)
            )
        )
        inscricoes = list(insc_res.scalars().all())

        deferidos = [i for i in inscricoes if i.avaliacao and i.avaliacao.parecer == "DEFERIDO"]
        # Ordenação conforme RN-09
        deferidos.sort(
            key=lambda i: (
                -(i.avaliacao.nota_merito or Decimal("0.00")),
                -(i.cr_congelado or Decimal("0.00")),
                i.data_submissao_original
            )
        )

        vagas = edital.vagas
        titulares_data = []
        suplentes_data = []

        for pos, i in enumerate(deferidos, start=1):
            item = {
                "posicao": pos,
                "inscricao_id": i.id,
                "protocolo": i.protocolo,
                "nome_estudante": i.estudante.nome,
                "matricula": i.estudante.matricula,
                "curso": i.curso_congelado or "",
                "cr": i.cr_congelado or Decimal("0.00"),
                "nota_merito": i.avaliacao.nota_merito or Decimal("0.00"),
            }
            if pos <= vagas:
                titulares_data.append(item)
            else:
                suplentes_data.append(item)

        # 3. Busca usuário pró-reitor
        pr_res = await db.execute(select(Usuario).where(Usuario.id == pro_reitor_id))
        pr_user = pr_res.scalar_one_or_none()
        pr_nome = pr_user.nome if pr_user else f"Pró-Reitor ID {pro_reitor_id}"

        now = datetime.now(timezone.utc)
        despacho = data.justificativa or "Homologo o resultado final do processo seletivo em conformidade com o edital."

        # 4. Gera Arquivo PDF da Ata Oficial (HOM-02)
        pdf_bytes = ReportService.gerar_ata_homologacao_pdf(
            edital_id=edital.id,
            edital_titulo=edital.titulo,
            homologador_nome=pr_nome,
            data_homologacao=now,
            titulares=titulares_data,
            suplentes=suplentes_data,
            despacho=despacho
        )

        # 5. Gera Arquivo CSV Oficial da Folha (HOM-02)
        csv_str = ReportService.gerar_folha_csv(
            edital_id=edital.id,
            edital_titulo=edital.titulo,
            valor_bolsa=edital.valor_bolsa,
            carga_horaria=edital.carga_horaria_semanal,
            titulares=titulares_data,
            suplentes=suplentes_data
        )
        csv_bytes = csv_str.encode("utf-8")

        # 6. Salva no ArmazenamentoDisco
        storage = get_storage_service()

        chave_pdf = f"editais/{edital.id}/atas/ata_homologacao_{uuid.uuid4()}.pdf"
        await storage.save_file_stream(chave_pdf, pdf_bytes)
        arq_pdf = Arquivo(
            chave=chave_pdf,
            nome_original=f"ata_homologacao_edital_{edital.id}.pdf",
            sha256=hashlib.sha256(pdf_bytes).hexdigest(),
            tamanho_bytes=len(pdf_bytes),
            content_type="application/pdf",
            versao=1,
            ativo=True,
            status_varredura="VALIDADO",
        )
        db.add(arq_pdf)
        await db.flush()

        chave_csv = f"editais/{edital.id}/atas/lista_aprovados_{uuid.uuid4()}.csv"
        await storage.save_file_stream(chave_csv, csv_bytes)
        arq_csv = Arquivo(
            chave=chave_csv,
            nome_original=f"lista_aprovados_edital_{edital.id}.csv",
            sha256=hashlib.sha256(csv_bytes).hexdigest(),
            tamanho_bytes=len(csv_bytes),
            content_type="text/csv",
            versao=1,
            ativo=True,
            status_varredura="VALIDADO",
        )
        db.add(arq_csv)
        await db.flush()

        # 7. Registra ata de homologação
        ata = AtaHomologacao(
            edital_id=edital.id,
            homologado_por=pro_reitor_id,
            arquivo_pdf_id=arq_pdf.id,
            arquivo_csv_id=arq_csv.id,
            eh_retificacao=False,
            justificativa_retificacao=None,
            homologado_em=now,
        )
        db.add(ata)

        # 8. Atualiza edital para ENCERRADO (resultado imutável - RN-13)
        edital.status = "ENCERRADO"

        # Notifica inscritos
        for insc in inscricoes:
            notif = Notificacao(
                usuario_id=insc.estudante_id,
                tipo="RESULTADO_FINAL",
                titulo=f"Processo Seletivo Homologado - {edital.titulo}",
                mensagem=f"O resultado final foi homologado oficialmente pela Pró-Reitoria. Consulte a ata e listas disponíveis."
            )
            db.add(notif)

        await log_audit_action(
            db=db,
            usuario_id=pro_reitor_id,
            acao="HOMOLOGAR_RESULTADO_FINAL",
            entidade="editais",
            entidade_id=edital.id,
            dados_depois={"status": "ENCERRADO", "ata_id": ata.id, "titulares": len(titulares_data), "suplentes": len(suplentes_data)},
            ip_origem=ip_origem,
        )

        await db.commit()
        await db.refresh(ata)
        return ata

    @staticmethod
    async def devolver_ajustes(
        db: AsyncSession,
        edital_id: int,
        pro_reitor_id: int,
        data: DevolverAjustesRequest,
        ip_origem: str = "127.0.0.1"
    ) -> Edital:
        """
        Devolve edital de EM_HOMOLOGACAO_FINAL de volta para EM_AVALIACAO com justificativa (HOM-01, §7.1).
        """
        edital_res = await db.execute(select(Edital).where(Edital.id == edital_id))
        edital = edital_res.scalar_one_or_none()
        if not edital:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edital não encontrado.")

        if edital.status != "EM_HOMOLOGACAO_FINAL":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Apenas editais em EM_HOMOLOGACAO_FINAL podem ser devolvidos para ajustes. Estado atual: {edital.status}."
            )

        edital.status = "EM_AVALIACAO"

        await log_audit_action(
            db=db,
            usuario_id=pro_reitor_id,
            acao="DEVOLVER_EDITAL_AJUSTES",
            entidade="editais",
            entidade_id=edital.id,
            dados_antes={"status": "EM_HOMOLOGACAO_FINAL"},
            dados_depois={"status": "EM_AVALIACAO", "justificativa": data.justificativa},
            ip_origem=ip_origem,
        )

        await db.commit()
        await db.refresh(edital)
        return edital
