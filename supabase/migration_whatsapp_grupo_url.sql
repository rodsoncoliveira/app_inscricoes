-- Execute no Supabase se o projeto já existia antes desta coluna.
ALTER TABLE eventos ADD COLUMN IF NOT EXISTS whatsapp_grupo_url TEXT;
