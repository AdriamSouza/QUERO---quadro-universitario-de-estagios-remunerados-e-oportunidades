import csv
import io
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any, Optional
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.core.pdf import build_text_pdf

SEPARADOR = "=" * 88
LINHA = "-" * 88
CABECALHO = "QUERO - QUADRO UNIVERSITÁRIO DE ESTÁGIOS REMUNERADOS E OPORTUNIDADES"


def _local(dt: Optional[datetime] = None) -> datetime:
    dt = dt or datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ZoneInfo(settings.TIMEZONE))


def _fmt(dt: Optional[datetime] = None) -> str:
    return _local(dt).strftime("%d/%m/%Y às %H:%M:%S")


def _csv_safe(value: Any) -> str:
    """Neutraliza injeção de fórmulas em planilhas (CSV injection)."""
    s = "" if value is None else str(value)
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


class ReportService:

    @staticmethod
    def gerar_folha_csv(
        edital_id: int,
        edital_titulo: str,
        valor_bolsa: Decimal,
        carga_horaria: int,
        titulares: List[Dict[str, Any]],
        suplentes: List[Dict[str, Any]]
    ) -> str:
        """Lista oficial de contemplados e suplentes em CSV (separador ';', compatível com Excel)."""
        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=";", quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
        writer.writerow([f"# {CABECALHO}"])
        writer.writerow([f"# Edital #{edital_id}: {_csv_safe(edital_titulo)} - Emissão: {_local().strftime('%d/%m/%Y %H:%M:%S')}"])
        writer.writerow([
            "Posicao", "Situacao", "Protocolo", "Nome", "Matricula", "Curso",
            "CR", "NotaMerito", "ValorMensal_Bolsa", "CargaHorariaSemanal",
        ])

        def _row(item: Dict[str, Any], situacao: str, valor: Decimal):
            writer.writerow([
                item["posicao"],
                situacao,
                _csv_safe(item["protocolo"]),
                _csv_safe(item["nome_estudante"]),
                _csv_safe(item.get("matricula") or "-"),
                _csv_safe(item.get("curso") or ""),
                f"{float(item.get('cr') or 0):.2f}",
                f"{float(item.get('nota_merito') or 0):.2f}",
                f"{float(valor):.2f}",
                f"{carga_horaria}h",
            ])

        for item in titulares:
            _row(item, "CONTEMPLADO", valor_bolsa)
        for item in suplentes:
            _row(item, "SUPLENTE", Decimal("0"))

        return buffer.getvalue()

    @staticmethod
    def gerar_ata_homologacao_pdf(
        edital_id: int,
        edital_titulo: str,
        homologador_nome: str,
        data_homologacao: datetime,
        titulares: List[Dict[str, Any]],
        suplentes: List[Dict[str, Any]],
        despacho: str
    ) -> bytes:
        """Ata Oficial de Homologação em PDF."""

        def _linha(item: Dict[str, Any]) -> str:
            return (
                f"  [{item['posicao']:02d}] {item['nome_estudante']} (Matrícula: {item.get('matricula') or '-'})\n"
                f"       Curso: {item.get('curso') or '-'} | Nota: {float(item['nota_merito']):.2f} | "
                f"Protocolo: {item['protocolo']}"
            )

        linhas_titulares = "\n".join(_linha(t) for t in titulares) or "  Nenhum candidato contemplado."
        linhas_suplentes = "\n".join(_linha(s) for s in suplentes) or "  Nenhum suplente."

        corpo = f"""{SEPARADOR}
{CABECALHO}
PRÓ-REITORIA DE GRADUAÇÃO
{SEPARADOR}

ATA DE HOMOLOGAÇÃO DO RESULTADO FINAL - EDITAL #{edital_id}

Título: {edital_titulo}
Data e hora da homologação: {_fmt(data_homologacao)} (horário de Brasília)
Autoridade homologadora: {homologador_nome}

DESPACHO:
"{despacho}"

{LINHA}
QUADRO I - CANDIDATOS CONTEMPLADOS
{LINHA}
{linhas_titulares}

{LINHA}
QUADRO II - CADASTRO DE RESERVA (SUPLENTES)
{LINHA}
{linhas_suplentes}

{LINHA}
TERMO DE HOMOLOGAÇÃO E ENCERRAMENTO
O presente documento homologa o resultado final e encerra o processo seletivo
regido pelo Edital #{edital_id}.
{SEPARADOR}
"""
        return build_text_pdf(corpo, footer=f"Ata de Homologação - Edital #{edital_id}")

    @staticmethod
    def gerar_comprovante_inscricao_pdf(
        protocolo: str,
        edital_id: int,
        edital_titulo: str,
        nome: str,
        matricula: Optional[str],
        curso: Optional[str],
        cr: Optional[Decimal],
        data_submissao: datetime,
        data_retificacao: Optional[datetime],
        situacao: str,
        documentos: List[str],
    ) -> bytes:
        docs = "\n".join(f"  - {d}" for d in documentos) or "  (nenhum documento anexado)"
        retificacao = f"\nÚltima retificação: {_fmt(data_retificacao)}" if data_retificacao else ""
        corpo = f"""{SEPARADOR}
{CABECALHO}
{SEPARADOR}

COMPROVANTE DE INSCRIÇÃO

Protocolo: {protocolo}
Edital: #{edital_id} - {edital_titulo}
Candidato(a): {nome}
Matrícula: {matricula or "-"}
Curso: {curso or "-"}
CR considerado: {float(cr or 0):.2f}
Data/hora da inscrição: {_fmt(data_submissao)} (horário de Brasília){retificacao}
Situação na emissão: {situacao}

Documentos enviados:
{docs}

{LINHA}
Documento emitido eletronicamente em {_fmt()}.
A autenticidade pode ser verificada junto à Pró-Reitoria pelo número de protocolo.
{SEPARADOR}
"""
        return build_text_pdf(corpo, font_size=10, leading=14, footer=f"Comprovante {protocolo}")
