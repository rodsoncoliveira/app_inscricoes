-- Migração: oficinas reutilizáveis em múltiplos eventos
-- Execute no Supabase SQL Editor se o banco já existia com oficinas.evento_id

CREATE TABLE IF NOT EXISTS evento_oficinas (
    evento_id INTEGER NOT NULL REFERENCES eventos(id) ON DELETE CASCADE,
    oficina_id INTEGER NOT NULL REFERENCES oficinas(id) ON DELETE CASCADE,
    vagas INTEGER NOT NULL,
    preletor TEXT,
    PRIMARY KEY (evento_id, oficina_id)
);

CREATE INDEX IF NOT EXISTS idx_evento_oficinas_evento ON evento_oficinas(evento_id);
CREATE INDEX IF NOT EXISTS idx_evento_oficinas_oficina ON evento_oficinas(oficina_id);

ALTER TABLE oficinas ADD COLUMN IF NOT EXISTS descricao TEXT;
ALTER TABLE oficinas ADD COLUMN IF NOT EXISTS ativo INTEGER DEFAULT 1;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'oficinas' AND column_name = 'evento_id'
    ) THEN
        INSERT INTO evento_oficinas (evento_id, oficina_id, vagas)
        SELECT evento_id, id, vagas
        FROM oficinas
        WHERE evento_id IS NOT NULL
        ON CONFLICT (evento_id, oficina_id) DO NOTHING;

        ALTER TABLE oficinas DROP COLUMN evento_id;
        ALTER TABLE oficinas DROP COLUMN vagas;
    END IF;
END $$;
