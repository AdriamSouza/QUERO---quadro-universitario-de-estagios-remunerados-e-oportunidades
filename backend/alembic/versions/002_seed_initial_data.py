"""seed dados iniciais e usuarios mock v5.0 - QUERO

Revision ID: 002_seed_initial_data
Revises: 001_initial_schema
Create Date: 2026-11-24 18:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision: str = "002_seed_initial_data"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Inserir usuários padrão/mock (v5.0 §2.2)
    op.execute(text("""
        INSERT INTO usuarios (id, cpf, matricula, nome, email, perfil, ativo, criado_em)
        VALUES 
            (1, '11122233344', '2024001001', 'João Silva', 'estudante@faculdade.edu.br', 'ESTUDANTE', true, NOW()),
            (2, '22233344455', '1998002002', 'Prof. Carlos Avaliador', 'avaliador@faculdade.edu.br', 'AVALIADOR', true, NOW()),
            (3, '33344455566', '1990003003', 'Dra. Maria Pró-Reitora', 'proreitor@faculdade.edu.br', 'PRO_REITOR', true, NOW())
        ON CONFLICT (email) DO NOTHING;
    """))

    # Ajustar a sequence de ID para não colidir
    op.execute(text("""
        SELECT setval(pg_get_serial_sequence('usuarios', 'id'), COALESCE((SELECT MAX(id) FROM usuarios), 1));
    """))

    # 2. Inserir editais iniciais abertos para vitrine (v5.0 EDT-01, EDT-02)
    op.execute(text("""
        INSERT INTO editais (
            id, titulo, descricao, categoria, modalidade, valor_bolsa,
            carga_horaria_semanal, vagas, cr_minimo, prazo_recurso_horas,
            criterios_pontuacao, criterios_desempate, status,
            data_inicio_inscricao, data_fim_inscricao,
            data_inicio_avaliacao, data_resultado_preliminar, data_homologacao_final,
            criado_por, criado_em
        ) VALUES (
            1,
            'Edital 01/2026 - Monitoria e Apoio Pedagógico em Sistemas de Informação',
            'Processo seletivo simplificado para preenchimento de bolsas de monitoria e tutoria acadêmica para disciplinas do curso de Sistemas de Informação.',
            'MONITORIA',
            'Presencial',
            700.00,
            20,
            5,
            7.00,
            48,
            '{"CR": 0.6, "Entrevista": 0.4}'::jsonb,
            '["MAIOR_CR", "MAIOR_CH_CONCLUIDA", "MAIOR_IDADE"]'::jsonb,
            'ABERTO',
            NOW() - INTERVAL '2 days',
            NOW() + INTERVAL '14 days',
            NOW() + INTERVAL '15 days',
            NOW() + INTERVAL '20 days',
            NOW() + INTERVAL '25 days',
            3,
            NOW()
        ), (
            2,
            'Edital 02/2026 - Estágio Universitário Remunerado em Desenvolvimento de Software & TI',
            'Seleção de estagiários remunerados para desenvolvimento de sistemas web institucionais, suporte e automação de serviços em cooperação técnica.',
            'ESTAGIO',
            'Híbrido',
            1400.00,
            30,
            3,
            6.50,
            48,
            '{"CR": 0.5, "Prova_Tecnica": 0.5}'::jsonb,
            '["MAIOR_CR", "MAIOR_CH_CONCLUIDA", "MAIOR_IDADE"]'::jsonb,
            'ABERTO',
            NOW() - INTERVAL '1 day',
            NOW() + INTERVAL '20 days',
            NOW() + INTERVAL '21 days',
            NOW() + INTERVAL '28 days',
            NOW() + INTERVAL '35 days',
            3,
            NOW()
        )
        ON CONFLICT (id) DO NOTHING;
    """))

    # Ajustar a sequence de ID de editais
    op.execute(text("""
        SELECT setval(pg_get_serial_sequence('editais', 'id'), COALESCE((SELECT MAX(id) FROM editais), 1));
    """))

    # 3. Cursos autorizados para os editais
    op.execute(text("""
        INSERT INTO edital_cursos (edital_id, codigo_curso, nome_curso)
        VALUES 
            (1, 'SI', 'Sistemas de Informação'),
            (2, 'SI', 'Sistemas de Informação'),
            (2, 'CC', 'Ciência da Computação')
        ON CONFLICT (edital_id, codigo_curso) DO NOTHING;
    """))

    # 4. Documentos exigidos para os editais
    op.execute(text("""
        INSERT INTO edital_documentos_exigidos (edital_id, nome, descricao, obrigatorio)
        VALUES 
            (1, 'Histórico Escolar Atualizado', 'Histórico oficial com CR acumulado emitido pelo sistema acadêmico SIGA', true),
            (2, 'Histórico Escolar Atualizado', 'Histórico emitido pelo SIGA com disciplinas concluídas e CR', true),
            (2, 'Currículo Profissional / Lattes', 'Currículo detalhando conhecimentos em linguagens de programação e projetos', true)
        ON CONFLICT DO NOTHING;
    """))

    # 5. Designar comissão avaliadora inicial
    op.execute(text("""
        INSERT INTO comissao_edital (edital_id, avaliador_id, designado_por, designado_em)
        VALUES 
            (1, 2, 3, NOW()),
            (2, 2, 3, NOW())
        ON CONFLICT (edital_id, avaliador_id) DO NOTHING;
    """))


def downgrade() -> None:
    op.execute(text("DELETE FROM comissao_edital WHERE edital_id IN (1, 2);"))
    op.execute(text("DELETE FROM edital_documentos_exigidos WHERE edital_id IN (1, 2);"))
    op.execute(text("DELETE FROM edital_cursos WHERE edital_id IN (1, 2);"))
    op.execute(text("DELETE FROM editais WHERE id IN (1, 2);"))
    op.execute(text("DELETE FROM usuarios WHERE id IN (1, 2, 3);"))
