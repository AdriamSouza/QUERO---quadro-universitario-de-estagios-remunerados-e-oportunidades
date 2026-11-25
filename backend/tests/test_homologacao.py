import csv
import io
import re
from datetime import datetime, timezone
from decimal import Decimal

from app.core.pdf import build_text_pdf
from app.routers._download import content_disposition
from app.services.report_service import ReportService

TITULARES = [{
    "posicao": 1, "protocolo": "QUERO-0001-00001", "nome_estudante": "João Silva", "matricula": "2024001001",
    "curso": "Ciência da Computação", "cr": Decimal("8.50"), "nota_merito": Decimal("9.20"),
}]
SUPLENTES = [{
    "posicao": 2, "protocolo": "QUERO-0001-00002", "nome_estudante": "Maria; \"Duda\" Eduarda", "matricula": "2023002002",
    "curso": "=HYPERLINK(\"x\")", "cr": Decimal("7.80"), "nota_merito": Decimal("8.40"),
}]


def test_gerar_folha_csv_format_e_escape():
    out = ReportService.gerar_folha_csv(1, "Edital Monitoria 2026", Decimal("700.00"), 20, TITULARES, SUPLENTES)
    assert "1;CONTEMPLADO;QUERO-0001-00001;João Silva;2024001001;Ciência da Computação;8.50;9.20;700.00;20h" in out

    linhas = list(csv.reader(io.StringIO(out), delimiter=";"))
    suplente = next(l for l in linhas if len(l) > 1 and l[1] == "SUPLENTE")
    assert suplente[3] == 'Maria; "Duda" Eduarda'      # separador e aspas preservados como dado
    assert suplente[5].startswith("'=")               # fórmula neutralizada
    assert suplente[8] == "0.00"


def _validar_xref(pdf: bytes) -> int:
    pos = int(re.search(rb"startxref\n(\d+)", pdf).group(1))
    linhas = pdf[pos:].split(b"\n")
    assert linhas[0] == b"xref"
    total = int(linhas[1].split()[1])
    for i, linha in enumerate(linhas[3:3 + total - 1], start=1):
        assert pdf[int(linha[:10]):].startswith(f"{i} 0 obj".encode())
    return total


def test_gerar_ata_homologacao_pdf():
    pdf = ReportService.gerar_ata_homologacao_pdf(
        1, "Edital (Monitoria) 2026", "Dra. Maria", datetime.now(timezone.utc), TITULARES, SUPLENTES * 200, "Homologo.",
    )
    assert pdf.startswith(b"%PDF-1.4") and pdf.rstrip().endswith(b"%%EOF")
    assert b"QUERO" in pdf
    assert b"Edital \\(Monitoria\\) 2026" in pdf
    _validar_xref(pdf)
    assert pdf.count(b"/Type /Page ") > 1  # lista longa gera várias páginas


def test_comprovante_pdf_com_acentos():
    pdf = ReportService.gerar_comprovante_inscricao_pdf(
        "QUERO-0001-00001", 1, "Edital", "José (Zé) Ação", "123", "SI", Decimal("8.1"),
        datetime.now(timezone.utc), None, "Homologada", ["Histórico: hist.pdf (versão 1)"],
    )
    assert "Ação".encode("cp1252") in pdf
    _validar_xref(pdf)


def test_pdf_vazio_tem_uma_pagina():
    pdf = build_text_pdf("")
    assert pdf.count(b"/Type /Page ") == 1


def test_content_disposition_seguro():
    header = content_disposition('relatório "final"\r\n.pdf')
    assert "\r" not in header and "\n" not in header
    assert 'filename="relat_rio _final___.pdf"' in header
    assert "filename*=UTF-8''relat%C3%B3rio" in header
