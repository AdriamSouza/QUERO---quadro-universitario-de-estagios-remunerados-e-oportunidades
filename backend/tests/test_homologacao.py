import pytest
from decimal import Decimal
from datetime import datetime, timezone
from app.services.report_service import ReportService


def test_gerar_folha_csv_format():
    """Valida formato oficial da lista em CSV (HOM-02)."""
    titulares = [
        {
            "posicao": 1,
            "protocolo": "QUERO-0001-00001",
            "nome_estudante": "João Silva",
            "matricula": "2024001001",
            "curso": "Ciência da Computação",
            "cr": Decimal("8.50"),
            "nota_merito": Decimal("9.20")
        }
    ]
    suplentes = [
        {
            "posicao": 2,
            "protocolo": "QUERO-0001-00002",
            "nome_estudante": "Maria Eduarda",
            "matricula": "2023002002",
            "curso": "Sistemas de Informação",
            "cr": Decimal("7.80"),
            "nota_merito": Decimal("8.40")
        }
    ]

    csv_output = ReportService.gerar_folha_csv(
        edital_id=1,
        edital_titulo="Edital Monitoria 2026",
        valor_bolsa=Decimal("700.00"),
        carga_horaria=20,
        titulares=titulares,
        suplentes=suplentes
    )

    assert "QUERO" in csv_output
    assert "1;CONTEMPLADO;QUERO-0001-00001;João Silva;2024001001;Ciência da Computação;8.50;9.20;700.00;20h" in csv_output
    assert "2;SUPLENTE;QUERO-0001-00002;Maria Eduarda;2023002002;Sistemas de Informação;7.80;8.40;0.00;20h" in csv_output


def test_gerar_ata_homologacao_pdf_bytes():
    """Valida se o gerador de Ata produz um binário PDF legítimo (%PDF-1.4)."""
    titulares = [
        {
            "posicao": 1,
            "protocolo": "QUERO-0001-00001",
            "nome_estudante": "João Silva",
            "matricula": "2024001001",
            "curso": "Ciência da Computação",
            "nota_merito": Decimal("9.20")
        }
    ]
    suplentes = []

    pdf_bytes = ReportService.gerar_ata_homologacao_pdf(
        edital_id=1,
        edital_titulo="Edital Monitoria 2026",
        homologador_nome="Dra. Maria Pró-Reitora",
        data_homologacao=datetime.now(timezone.utc),
        titulares=titulares,
        suplentes=suplentes,
        despacho="Homologo o resultado final."
    )

    assert pdf_bytes.startswith(b"%PDF-1.4")
    assert b"%%EOF" in pdf_bytes
    assert b"QUERO" in pdf_bytes
