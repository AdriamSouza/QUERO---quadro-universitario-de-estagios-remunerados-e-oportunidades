import io
import hashlib
from datetime import datetime
from typing import List, Dict, Any
from decimal import Decimal


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
        """
        Gera o arquivo CSV oficial dos resultados homologados (HOM-02, v5.0 §10).
        Utiliza delimitador ';' e cabeçalho UTF-8.
        """
        lines = [
            f"# QUERO - QUADRO UNIVERSITÁRIO DE ESTÁGIOS REMUNERADOS E OPORTUNIDADES",
            f"# Edital #{edital_id}: {edital_titulo} - Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            "Posicao;Situacao;Protocolo;Nome;Matricula;Curso;CR;NotaMerito;ValorMensal_Bolsa;CargaHorariaSemanal"
        ]

        for item in titulares:
            matricula = item.get("matricula") or "-"
            cr = float(item.get("cr", 0.0))
            nota = float(item.get("nota_merito", 0.0))
            lines.append(
                f"{item['posicao']};CONTEMPLADO;{item['protocolo']};{item['nome_estudante']};{matricula};{item['curso']};{cr:.2f};{nota:.2f};{float(valor_bolsa):.2f};{carga_horaria}h"
            )

        for item in suplentes:
            matricula = item.get("matricula") or "-"
            cr = float(item.get("cr", 0.0))
            nota = float(item.get("nota_merito", 0.0))
            lines.append(
                f"{item['posicao']};SUPLENTE;{item['protocolo']};{item['nome_estudante']};{matricula};{item['curso']};{cr:.2f};{nota:.2f};0.00;{carga_horaria}h"
            )

        return "\r\n".join(lines)

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
        """
        Gera a Ata Oficial de Homologação em formato PDF padronizado com %PDF-1.4 (HOM-02).
        """
        data_fmt = data_homologacao.strftime("%d/%m/%Y as %H:%M:%S")

        linhas_titulares = "\n".join([
            f"  [{t['posicao']:02d}] {t['nome_estudante']} (Matricula: {t.get('matricula') or '-'}) - Curso: {t['curso']} | Nota: {float(t['nota_merito']):.2f} | Protocolo: {t['protocolo']}"
            for t in titulares
        ]) or "  Nenhum candidato contemplado."

        linhas_suplentes = "\n".join([
            f"  [{s['posicao']:02d}] {s['nome_estudante']} (Matricula: {s.get('matricula') or '-'}) - Curso: {s['curso']} | Nota: {float(s['nota_merito']):.2f} | Protocolo: {s['protocolo']}"
            for s in suplentes
        ]) or "  Nenhum suplente cadastrado."

        corpo_ata = f"""
================================================================================
          QUERO - QUADRO UNIVERSITARIO DE ESTAGIOS REMUNERADOS E OPORTUNIDADES
               PRÓ-REITORIA DE GRADUAÇÃO / GESTÃO ACADÊMICA
================================================================================

               ATA OFICIAL DE HOMOLOGAÇÃO DE RESULTADO FINAL
                              EDITAL #{edital_id}

Titulo: {edital_titulo}
Data e Hora da Homologacao: {data_fmt} (Horario Oficial de Brasilia)
Autoridade Homologadora: {homologador_nome}

DESPACHO ADMINISTRATIVO:
"{despacho}"

--------------------------------------------------------------------------------
QUADRO I - CANDIDATOS CONTEMPLADOS
--------------------------------------------------------------------------------
{linhas_titulares}

--------------------------------------------------------------------------------
QUADRO II - BANCO DE SUPLENTES
--------------------------------------------------------------------------------
{linhas_suplentes}

--------------------------------------------------------------------------------
TERMO DE HOMOLOGAÇÃO E ENCERRAMENTO:
O presente documento oficializa de forma imutavel o encerramento do processo
seletivo regulamentado pelo presente Edital nos termos do Documento de Projeto v5.0.
================================================================================
"""
        corpo_escaped = (
            corpo_ata.replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
            .encode("latin-1", errors="replace")
            .decode("latin-1")
        )

        stream_content = f"BT /F1 9 Tf 36 760 Td 13 TL\n"
        for linha in corpo_escaped.split("\n"):
            stream_content += f"({linha}) '\n"
        stream_content += "ET"
        stream_bytes = stream_content.encode("latin-1", errors="replace")
        stream_len = len(stream_bytes)

        header_bytes = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
        stream_obj = (
            f"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            f"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            f"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n"
            f"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>\nendobj\n"
            f"5 0 obj\n<< /Length {stream_len} >>\nstream\n"
        ).encode("ascii") + stream_bytes + b"\nendstream\nendobj\n"

        trailer_bytes = (
            f"xref\n0 6\n0000000000 65535 f \n"
            f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{len(header_bytes) + len(stream_obj)}\n%%EOF"
        ).encode("ascii")

        return header_bytes + stream_obj + trailer_bytes
