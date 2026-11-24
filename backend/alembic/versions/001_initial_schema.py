"""esquema inicial ddl v5.0 - QUERO

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-24 16:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. Extensões e Sequências Atômicas
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.execute('CREATE SEQUENCE IF NOT EXISTS seq_protocolo_inscricao START WITH 1 INCREMENT BY 1;')

    # 1. Usuários (SSO em produção; senha_hash em dev/contingência com Argon2id/bcrypt)
    op.create_table(
        'usuarios',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('sso_sub', sa.String(120), unique=True, nullable=True),
        sa.Column('cpf', sa.String(11), unique=True, nullable=False),
        sa.Column('matricula', sa.String(40), unique=True, nullable=True),
        sa.Column('nome', sa.String(150), nullable=False),
        sa.Column('email', sa.String(120), unique=True, nullable=False),
        sa.Column('senha_hash', sa.String(255), nullable=True),
        sa.Column('perfil', sa.String(20), nullable=False),
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('criado_em', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint("perfil IN ('ESTUDANTE', 'AVALIADOR', 'PRO_REITOR')", name='chk_usuarios_perfil')
    )

    # 2. Editais
    op.create_table(
        'editais',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('titulo', sa.String(200), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=False),
        sa.Column('categoria', sa.String(30), nullable=False),
        sa.Column('modalidade', sa.String(50), nullable=False),
        sa.Column('valor_bolsa', sa.Numeric(10, 2), nullable=False),
        sa.Column('carga_horaria_semanal', sa.Integer(), nullable=False),
        sa.Column('vagas', sa.Integer(), nullable=False),
        sa.Column('cr_minimo', sa.Numeric(4, 2), nullable=False),
        sa.Column('prazo_recurso_horas', sa.Integer(), nullable=False, server_default=sa.text('48')),
        sa.Column('criterios_pontuacao', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('criterios_desempate', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[\"CR_DESC\", \"SUBMISSAO_ASC\"]'::jsonb")),
        sa.Column('status', sa.String(30), nullable=False, server_default='RASCUNHO'),
        sa.Column('data_inicio_inscricao', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('data_fim_inscricao', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('data_inicio_avaliacao', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('data_resultado_preliminar', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('data_homologacao_final', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('justificativa_cancelamento', sa.Text(), nullable=True),
        sa.Column('criado_por', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=False),
        sa.Column('criado_em', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint("categoria IN ('ESTAGIO', 'MONITORIA', 'BOLSA')", name='chk_editais_categoria'),
        sa.CheckConstraint('valor_bolsa >= 0', name='chk_editais_valor_bolsa'),
        sa.CheckConstraint('carga_horaria_semanal > 0', name='chk_editais_carga_horaria'),
        sa.CheckConstraint('vagas > 0', name='chk_editais_vagas'),
        sa.CheckConstraint('cr_minimo >= 0 AND cr_minimo <= 10', name='chk_editais_cr_minimo'),
        sa.CheckConstraint('prazo_recurso_horas > 0', name='chk_editais_prazo_recurso'),
        sa.CheckConstraint(
            "status IN ('RASCUNHO', 'ABERTO', 'INSCRICOES_ENCERRADAS', 'EM_AVALIACAO', 'RESULTADO_PRELIMINAR', 'EM_RECURSO', 'EM_HOMOLOGACAO_FINAL', 'ENCERRADO', 'CANCELADO')",
            name='chk_editais_status'
        )
    )

    # 3. Cursos autorizados por edital
    op.create_table(
        'edital_cursos',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('edital_id', sa.Integer(), sa.ForeignKey('editais.id', ondelete='CASCADE'), nullable=False),
        sa.Column('codigo_curso', sa.String(40), nullable=False),
        sa.Column('nome_curso', sa.String(120), nullable=False),
        sa.UniqueConstraint('edital_id', 'codigo_curso', name='unq_edital_curso')
    )

    # 4. Documentos exigidos por edital
    op.create_table(
        'edital_documentos_exigidos',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('edital_id', sa.Integer(), sa.ForeignKey('editais.id', ondelete='CASCADE'), nullable=False),
        sa.Column('nome', sa.String(120), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('obrigatorio', sa.Boolean(), nullable=False, server_default=sa.text('true'))
    )

    # 5. Comissão avaliadora por edital
    op.create_table(
        'comissao_edital',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('edital_id', sa.Integer(), sa.ForeignKey('editais.id', ondelete='CASCADE'), nullable=False),
        sa.Column('avaliador_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=False),
        sa.Column('designado_por', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=False),
        sa.Column('designado_em', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.UniqueConstraint('edital_id', 'avaliador_id', name='unq_edital_avaliador')
    )

    # 6. Inscrições
    op.create_table(
        'inscricoes',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('protocolo', sa.String(50), unique=True, nullable=False),
        sa.Column('edital_id', sa.Integer(), sa.ForeignKey('editais.id'), nullable=False),
        sa.Column('estudante_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=False),
        sa.Column('status', sa.String(35), nullable=False),
        sa.Column('motivos_indeferimento', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('vinculo_ativo_congelado', sa.Boolean(), nullable=True),
        sa.Column('curso_congelado', sa.String(120), nullable=True),
        sa.Column('cr_congelado', sa.Numeric(4, 2), nullable=True),
        sa.Column('data_submissao_original', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('data_ultima_retificacao', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('reanalisada_por', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        sa.Column('justificativa_reanalise', sa.Text(), nullable=True),
        sa.UniqueConstraint('edital_id', 'estudante_id', name='unq_edital_estudante'),
        sa.CheckConstraint(
            "status IN ('PENDENTE_VALIDACAO_VINCULO', 'HOMOLOGADA', 'INDEFERIDA', 'DESISTENTE')",
            name='chk_inscricoes_status'
        )
    )

    # 7. Metadados de arquivos
    op.create_table(
        'arquivos',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('inscricao_id', sa.Integer(), sa.ForeignKey('inscricoes.id', ondelete='CASCADE'), nullable=True),
        sa.Column('documento_exigido_id', sa.Integer(), sa.ForeignKey('edital_documentos_exigidos.id'), nullable=True),
        sa.Column('chave', sa.String(255), unique=True, nullable=False),
        sa.Column('nome_original', sa.String(255), nullable=False),
        sa.Column('sha256', sa.CHAR(64), nullable=False),
        sa.Column('tamanho_bytes', sa.BigInteger(), nullable=False),
        sa.Column('content_type', sa.String(100), nullable=False, server_default='application/pdf'),
        sa.Column('versao', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('status_varredura', sa.String(20), nullable=False, server_default='VALIDADO'),
        sa.Column('enviado_em', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint('tamanho_bytes > 0 AND tamanho_bytes <= 10485760', name='chk_arquivos_tamanho'),
        sa.CheckConstraint("status_varredura IN ('PENDENTE', 'VALIDADO', 'QUARENTENA', 'REJEITADO')", name='chk_arquivos_status_varredura')
    )

    # 8. Avaliações de mérito
    op.create_table(
        'avaliacoes',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('inscricao_id', sa.Integer(), sa.ForeignKey('inscricoes.id'), unique=True, nullable=False),
        sa.Column('avaliador_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=False),
        sa.Column('declaracao_sem_impedimento', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('nota_merito', sa.Numeric(4, 2), nullable=True),
        sa.Column('parecer', sa.String(20), nullable=True),
        sa.Column('justificativa', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='RASCUNHO'),
        sa.Column('justificativa_retificacao', sa.Text(), nullable=True),
        sa.Column('atualizado_em', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint('nota_merito >= 0 AND nota_merito <= 10', name='chk_avaliacoes_nota'),
        sa.CheckConstraint("parecer IN ('DEFERIDO', 'INDEFERIDO')", name='chk_avaliacoes_parecer'),
        sa.CheckConstraint("status IN ('RASCUNHO', 'CONFIRMADA', 'RETIFICADA')", name='chk_avaliacoes_status')
    )

    # 9. Recursos
    op.create_table(
        'recursos',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('inscricao_id', sa.Integer(), sa.ForeignKey('inscricoes.id'), unique=True, nullable=False),
        sa.Column('texto', sa.Text(), nullable=False),
        sa.Column('arquivo_anexo_id', sa.Integer(), sa.ForeignKey('arquivos.id'), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='ABERTO'),
        sa.Column('julgado_por', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        sa.Column('justificativa_decisao', sa.Text(), nullable=True),
        sa.Column('criado_em', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('julgado_em', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint('char_length(texto) <= 5000', name='chk_recursos_texto_length'),
        sa.CheckConstraint("status IN ('ABERTO', 'EM_ANALISE', 'DEFERIDO', 'INDEFERIDO')", name='chk_recursos_status')
    )

    # 10. Atas de homologação
    op.create_table(
        'atas_homologacao',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('edital_id', sa.Integer(), sa.ForeignKey('editais.id'), nullable=False),
        sa.Column('homologado_por', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=False),
        sa.Column('arquivo_pdf_id', sa.Integer(), sa.ForeignKey('arquivos.id'), nullable=False),
        sa.Column('arquivo_csv_id', sa.Integer(), sa.ForeignKey('arquivos.id'), nullable=False),
        sa.Column('eh_retificacao', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('justificativa_retificacao', sa.Text(), nullable=True),
        sa.Column('homologado_em', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()'))
    )

    # 11. Notificações
    op.create_table(
        'notificacoes',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=False),
        sa.Column('tipo', sa.String(50), nullable=False),
        sa.Column('titulo', sa.String(200), nullable=False),
        sa.Column('mensagem', sa.Text(), nullable=False),
        sa.Column('lida', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('email_status', sa.String(20), nullable=False, server_default='PENDENTE'),
        sa.Column('tentativas_email', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('criado_em', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint("email_status IN ('PENDENTE', 'ENVIADO', 'FALHA')", name='chk_notificacoes_email_status')
    )

    # 12. Trilha de Auditoria Imutável
    op.create_table(
        'auditoria_logs',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        sa.Column('acao', sa.String(60), nullable=False),
        sa.Column('entidade', sa.String(50), nullable=False),
        sa.Column('entidade_id', sa.Integer(), nullable=False),
        sa.Column('dados_antes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('dados_depois', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_origem', sa.String(45), nullable=True),
        sa.Column('criado_em', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()'))
    )

    # Índices Estratégicos
    op.create_index('idx_editais_status', 'editais', ['status'])
    op.create_index('idx_inscricoes_edital', 'inscricoes', ['edital_id'])
    op.create_index('idx_inscricoes_estudante', 'inscricoes', ['estudante_id'])
    op.create_index('idx_arquivos_chave', 'arquivos', ['chave'])
    op.create_index('idx_auditoria_entidade', 'auditoria_logs', ['entidade', 'entidade_id'])


def downgrade() -> None:
    op.drop_table('auditoria_logs')
    op.drop_table('notificacoes')
    op.drop_table('atas_homologacao')
    op.drop_table('recursos')
    op.drop_table('avaliacoes')
    op.drop_table('arquivos')
    op.drop_table('inscricoes')
    op.drop_table('comissao_edital')
    op.drop_table('edital_documentos_exigidos')
    op.drop_table('edital_cursos')
    op.drop_table('editais')
    op.drop_table('usuarios')
    op.execute('DROP SEQUENCE IF EXISTS seq_protocolo_inscricao;')
