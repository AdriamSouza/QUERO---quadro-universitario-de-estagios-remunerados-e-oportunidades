"""autenticação real, armazenamento persistente e janela de recurso

Revision ID: 003_auth_storage_workflow
Revises: 002_seed_initial_data
Create Date: 2026-11-25 10:00:00.000000

- editais.data_publicacao_preliminar: marca a abertura da janela de recurso (RN-10).
- arquivo_conteudos: conteúdo dos arquivos quando STORAGE_BACKEND=database.
- Ajusta as sequências de ID após a carga inicial com IDs explícitos.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

revision: str = "003_auth_storage_workflow"
down_revision: Union[str, None] = "002_seed_initial_data"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "editais",
        sa.Column("data_publicacao_preliminar", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    op.create_table(
        "arquivo_conteudos",
        sa.Column("chave", sa.String(255), primary_key=True),
        sa.Column("conteudo", sa.LargeBinary(), nullable=False),
        sa.Column("criado_em", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # Editais que já estavam em fase recursal passam a ter a janela contada a partir de agora.
    op.execute(text(
        "UPDATE editais SET data_publicacao_preliminar = NOW() "
        "WHERE status = 'EM_RECURSO' AND data_publicacao_preliminar IS NULL"
    ))

    for tabela in ("usuarios", "editais", "edital_cursos", "edital_documentos_exigidos", "comissao_edital"):
        op.execute(text(
            f"SELECT setval(pg_get_serial_sequence('{tabela}', 'id'), "
            f"COALESCE((SELECT MAX(id) FROM {tabela}), 1))"
        ))


def downgrade() -> None:
    op.drop_table("arquivo_conteudos")
    op.drop_column("editais", "data_publicacao_preliminar")
