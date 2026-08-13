-- Portal de Inscrições NextGen — schema PostgreSQL (Supabase)
-- Execute no Supabase: SQL Editor → New query → Run

CREATE TABLE IF NOT EXISTS eventos (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    descricao TEXT,
    data_inicio DATE,
    data_fim DATE,
    inicio_inscricoes DATE,
    fim_inscricoes DATE,
    banner_path TEXT,
    cor_primaria TEXT DEFAULT '#FF5733',
    cor_secundaria TEXT DEFAULT '#1e1e24',
    ativo INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS oficinas (
    id SERIAL PRIMARY KEY,
    evento_id INTEGER NOT NULL REFERENCES eventos(id) ON DELETE CASCADE,
    nome TEXT NOT NULL,
    preletor TEXT NOT NULL,
    vagas INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS inscricoes (
    id SERIAL PRIMARY KEY,
    evento_id INTEGER NOT NULL REFERENCES eventos(id) ON DELETE CASCADE,
    nome TEXT NOT NULL,
    data_nascimento DATE NOT NULL,
    whatsapp TEXT NOT NULL,
    igreja TEXT NOT NULL,
    responsavel_nome TEXT,
    responsavel_telefone TEXT,
    oficina_id INTEGER REFERENCES oficinas(id) ON DELETE SET NULL,
    oficina_id_2 INTEGER REFERENCES oficinas(id) ON DELETE SET NULL,
    data_inscricao TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inscricoes_evento_id ON inscricoes(evento_id);
CREATE INDEX IF NOT EXISTS idx_inscricoes_evento_nascimento ON inscricoes(evento_id, data_nascimento);
CREATE INDEX IF NOT EXISTS idx_oficinas_evento_id ON oficinas(evento_id);
