"""
Gerador mínimo de PDF textual (sem dependências externas).

Produz um PDF 1.4 válido: tabela xref com offsets corretos, várias páginas, fonte Courier com
codificação WinAnsi (acentos do português) e escape dos caracteres especiais do formato.
"""
import textwrap
from typing import List, Optional

PAGE_WIDTH = 595   # A4 em pontos
PAGE_HEIGHT = 842
MARGIN = 40


def _escape(line: str) -> bytes:
    raw = line.encode("cp1252", errors="replace")
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _wrap(lines: List[str], max_chars: int) -> List[str]:
    out: List[str] = []
    for line in lines:
        line = line.rstrip("\r").expandtabs(4)
        if len(line) <= max_chars:
            out.append(line)
            continue
        indent = len(line) - len(line.lstrip(" "))
        out.extend(
            textwrap.wrap(
                line, width=max_chars, subsequent_indent=" " * min(indent + 2, 20),
                break_long_words=True, replace_whitespace=False,
            ) or [""]
        )
    return out


def build_text_pdf(text: str, font_size: float = 9, leading: float = 12, footer: Optional[str] = None) -> bytes:
    char_width = font_size * 0.6  # Courier é monoespaçada
    max_chars = int((PAGE_WIDTH - 2 * MARGIN) / char_width)
    lines_per_page = int((PAGE_HEIGHT - 2 * MARGIN - leading * 2) / leading)

    lines = _wrap(text.split("\n"), max_chars)
    pages = [lines[i:i + lines_per_page] for i in range(0, len(lines), lines_per_page)] or [[""]]
    total = len(pages)

    objects: List[bytes] = []

    def add(obj: bytes) -> int:
        objects.append(obj)
        return len(objects)

    catalog_id = add(b"")  # preenchido depois
    pages_id = add(b"")
    font_id = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>")

    page_ids = []
    for idx, page_lines in enumerate(pages, start=1):
        stream = bytearray()
        stream += f"BT /F1 {font_size} Tf {leading} TL {MARGIN} {PAGE_HEIGHT - MARGIN} Td\n".encode("ascii")
        for line in page_lines:
            stream += b"(" + _escape(line) + b") '\n"
        stream += b"ET\n"
        rodape = f"{footer + ' - ' if footer else ''}Página {idx} de {total}"
        stream += f"BT /F1 7 Tf {MARGIN} {MARGIN // 2} Td (".encode("ascii") + _escape(rodape) + b") Tj ET\n"
        content_id = add(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + bytes(stream) + b"endstream")
        page_id = add(
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>".encode("ascii")
        )
        page_ids.append(page_id)

    objects[catalog_id - 1] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("ascii")
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects[pages_id - 1] = f"<< /Type /Pages /Kids [{kids}] /Count {total} >>".encode("ascii")

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for num, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{num} 0 obj\n".encode("ascii") + body + b"\nendobj\n"

    xref_pos = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode("ascii")
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode("ascii")
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    ).encode("ascii")
    return bytes(out)
