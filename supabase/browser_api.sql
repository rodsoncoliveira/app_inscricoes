-- API para site estático (GitHub Pages + Supabase JS)
-- Execute no Supabase SQL Editor após o schema principal.

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- ---------------------------------------------------------------------------
-- RLS
-- ---------------------------------------------------------------------------

ALTER TABLE eventos ENABLE ROW LEVEL SECURITY;
ALTER TABLE oficinas ENABLE ROW LEVEL SECURITY;
ALTER TABLE evento_oficinas ENABLE ROW LEVEL SECURITY;
ALTER TABLE inscricoes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS anon_read_eventos_abertos ON eventos;
CREATE POLICY anon_read_eventos_abertos ON eventos
    FOR SELECT TO anon
    USING (
        ativo = 1
        AND CURRENT_DATE >= inicio_inscricoes
        AND CURRENT_DATE <= fim_inscricoes
    );

DROP POLICY IF EXISTS anon_read_oficinas ON oficinas;
CREATE POLICY anon_read_oficinas ON oficinas
    FOR SELECT TO anon
    USING (true);

DROP POLICY IF EXISTS anon_read_evento_oficinas ON evento_oficinas;
CREATE POLICY anon_read_evento_oficinas ON evento_oficinas
    FOR SELECT TO anon
    USING (true);

DROP POLICY IF EXISTS admin_all_eventos ON eventos;
CREATE POLICY admin_all_eventos ON eventos
    FOR ALL TO authenticated
    USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS admin_all_oficinas ON oficinas;
CREATE POLICY admin_all_oficinas ON oficinas
    FOR ALL TO authenticated
    USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS admin_all_evento_oficinas ON evento_oficinas;
CREATE POLICY admin_all_evento_oficinas ON evento_oficinas
    FOR ALL TO authenticated
    USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS admin_all_inscricoes ON inscricoes;
CREATE POLICY admin_all_inscricoes ON inscricoes
    FOR ALL TO authenticated
    USING (true) WITH CHECK (true);

-- Anon não escreve direto nas tabelas (usa RPC).
DROP POLICY IF EXISTS anon_no_write_inscricoes ON inscricoes;
CREATE POLICY anon_no_write_inscricoes ON inscricoes
    FOR ALL TO anon
    USING (false) WITH CHECK (false);

-- ---------------------------------------------------------------------------
-- Helpers
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.is_minor(p_data_nascimento date)
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
    SELECT EXTRACT(YEAR FROM age(CURRENT_DATE, p_data_nascimento)) < 18;
$$;

CREATE OR REPLACE FUNCTION public.normalize_inscricao_nome(p_nome text)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT trim(
        regexp_replace(
            regexp_replace(
                lower(unaccent(trim(coalesce(p_nome, '')))),
                '[^a-z0-9\s]', ' ', 'g'
            ),
            '\s+', ' ', 'g'
        )
    );
$$;

CREATE OR REPLACE FUNCTION public.evento_aceita_inscricao(p_evento_id integer)
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1 FROM eventos e
        WHERE e.id = p_evento_id
          AND e.ativo = 1
          AND CURRENT_DATE >= e.inicio_inscricoes
          AND CURRENT_DATE <= e.fim_inscricoes
    );
$$;

CREATE OR REPLACE FUNCTION public.count_oficina_ocupacao(
    p_evento_id integer,
    p_oficina_id integer,
    p_exclude_id integer DEFAULT NULL
)
RETURNS integer
LANGUAGE sql
STABLE
AS $$
    SELECT COUNT(*)::integer
    FROM inscricoes i
    WHERE i.evento_id = p_evento_id
      AND (i.oficina_id = p_oficina_id OR i.oficina_id_2 = p_oficina_id)
      AND (p_exclude_id IS NULL OR i.id <> p_exclude_id);
$$;

-- ---------------------------------------------------------------------------
-- RPC: oficinas com vagas
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.get_oficinas_vagas(p_evento_id integer)
RETURNS TABLE (
    id integer,
    nome text,
    preletor text,
    vagas_totais integer,
    vagas_ocupadas integer,
    vagas_restantes integer
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT
        o.id,
        o.nome,
        COALESCE(eo.preletor, o.preletor) AS preletor,
        eo.vagas AS vagas_totais,
        public.count_oficina_ocupacao(p_evento_id, o.id, NULL) AS vagas_ocupadas,
        GREATEST(0, eo.vagas - public.count_oficina_ocupacao(p_evento_id, o.id, NULL)) AS vagas_restantes
    FROM evento_oficinas eo
    JOIN oficinas o ON o.id = eo.oficina_id
    WHERE eo.evento_id = p_evento_id
    ORDER BY o.nome;
$$;

GRANT EXECUTE ON FUNCTION public.get_oficinas_vagas(integer) TO anon, authenticated;

-- ---------------------------------------------------------------------------
-- RPC: criar ou atualizar inscrição (sem oficinas)
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.create_or_update_inscricao(
    p_evento_id integer,
    p_nome text,
    p_data_nascimento date,
    p_whatsapp text,
    p_igreja text,
    p_responsavel_nome text DEFAULT NULL,
    p_responsavel_telefone text DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_existing inscricoes%ROWTYPE;
    v_id integer;
    v_action text;
BEGIN
    IF NOT public.evento_aceita_inscricao(p_evento_id) THEN
        RETURN jsonb_build_object('ok', false, 'error', 'Inscrições encerradas ou evento indisponível.');
    END IF;

    IF trim(coalesce(p_nome, '')) = '' THEN
        RETURN jsonb_build_object('ok', false, 'error', 'Informe o nome completo.');
    END IF;

    IF public.is_minor(p_data_nascimento) THEN
        IF trim(coalesce(p_responsavel_nome, '')) = '' OR trim(coalesce(p_responsavel_telefone, '')) = '' THEN
            RETURN jsonb_build_object('ok', false, 'error', 'Menores de 18 anos devem informar nome e telefone do responsável.');
        END IF;
    END IF;

    SELECT i.* INTO v_existing
    FROM inscricoes i
    WHERE i.evento_id = p_evento_id
      AND i.data_nascimento = p_data_nascimento
      AND similarity(
        public.normalize_inscricao_nome(i.nome),
        public.normalize_inscricao_nome(p_nome)
      ) >= 0.88
    ORDER BY similarity(
        public.normalize_inscricao_nome(i.nome),
        public.normalize_inscricao_nome(p_nome)
      ) DESC
    LIMIT 1;

    IF FOUND THEN
        UPDATE inscricoes SET
            nome = trim(p_nome),
            whatsapp = trim(p_whatsapp),
            igreja = trim(p_igreja),
            responsavel_nome = NULLIF(trim(p_responsavel_nome), ''),
            responsavel_telefone = NULLIF(trim(p_responsavel_telefone), ''),
            data_inscricao = NOW()
        WHERE id = v_existing.id;
        v_id := v_existing.id;
        v_action := 'updated';
    ELSE
        INSERT INTO inscricoes (
            evento_id, nome, data_nascimento, whatsapp, igreja,
            responsavel_nome, responsavel_telefone
        ) VALUES (
            p_evento_id, trim(p_nome), p_data_nascimento, trim(p_whatsapp), trim(p_igreja),
            NULLIF(trim(p_responsavel_nome), ''), NULLIF(trim(p_responsavel_telefone), '')
        )
        RETURNING id INTO v_id;
        v_action := 'created';
    END IF;

    RETURN jsonb_build_object('ok', true, 'id', v_id, 'action', v_action);
END;
$$;

GRANT EXECUTE ON FUNCTION public.create_or_update_inscricao(integer, text, date, text, text, text, text) TO anon, authenticated;

-- ---------------------------------------------------------------------------
-- RPC: atualizar oficinas da inscrição
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.update_inscricao_oficinas(
    p_inscricao_id integer,
    p_oficina_id integer DEFAULT NULL,
    p_oficina_id_2 integer DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_row inscricoes%ROWTYPE;
    v_vagas integer;
    v_nome text;
    v_wid integer;
BEGIN
    SELECT * INTO v_row FROM inscricoes WHERE id = p_inscricao_id;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('ok', false, 'error', 'Inscrição não encontrada.');
    END IF;

    IF NOT public.evento_aceita_inscricao(v_row.evento_id) THEN
        RETURN jsonb_build_object('ok', false, 'error', 'Período de inscrições encerrado.');
    END IF;

    IF p_oficina_id IS NOT NULL AND p_oficina_id_2 IS NOT NULL AND p_oficina_id = p_oficina_id_2 THEN
        RETURN jsonb_build_object('ok', false, 'error', 'Selecione duas oficinas diferentes.');
    END IF;

    FOREACH v_wid IN ARRAY ARRAY[p_oficina_id, p_oficina_id_2] LOOP
        IF v_wid IS NULL THEN CONTINUE; END IF;
        IF NOT EXISTS (
            SELECT 1 FROM evento_oficinas eo
            WHERE eo.evento_id = v_row.evento_id AND eo.oficina_id = v_wid
        ) THEN
            SELECT nome INTO v_nome FROM oficinas WHERE id = v_wid;
            RETURN jsonb_build_object('ok', false, 'error', format('A oficina ''%s'' não está disponível neste evento.', coalesce(v_nome, 'Oficina')));
        END IF;
        IF v_wid IS DISTINCT FROM v_row.oficina_id AND v_wid IS DISTINCT FROM v_row.oficina_id_2 THEN
            SELECT eo.vagas INTO v_vagas FROM evento_oficinas eo
            WHERE eo.evento_id = v_row.evento_id AND eo.oficina_id = v_wid;
            IF public.count_oficina_ocupacao(v_row.evento_id, v_wid, p_inscricao_id) >= v_vagas THEN
                SELECT nome INTO v_nome FROM oficinas WHERE id = v_wid;
                RETURN jsonb_build_object('ok', false, 'error', format('A oficina ''%s'' já está lotada.', coalesce(v_nome, 'Oficina')));
            END IF;
        END IF;
    END LOOP;

    UPDATE inscricoes SET
        oficina_id = p_oficina_id,
        oficina_id_2 = p_oficina_id_2
    WHERE id = p_inscricao_id;

    RETURN jsonb_build_object('ok', true, 'id', p_inscricao_id);
END;
$$;

GRANT EXECUTE ON FUNCTION public.update_inscricao_oficinas(integer, integer, integer) TO anon, authenticated;

-- ---------------------------------------------------------------------------
-- RPC: resumo da inscrição (público, por id)
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.get_inscricao_resumo(p_inscricao_id integer)
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT jsonb_build_object(
        'id', i.id,
        'nome', i.nome,
        'data_nascimento', i.data_nascimento,
        'evento_nome', e.nome,
        'whatsapp_grupo_url', e.whatsapp_grupo_url,
        'oficina_nome', o1.nome,
        'oficina_preletor', COALESCE(eo1.preletor, o1.preletor),
        'oficina_nome_2', o2.nome,
        'oficina_preletor_2', COALESCE(eo2.preletor, o2.preletor),
        'responsavel_nome', i.responsavel_nome,
        'responsavel_telefone', i.responsavel_telefone
    )
    FROM inscricoes i
    JOIN eventos e ON e.id = i.evento_id
    LEFT JOIN oficinas o1 ON o1.id = i.oficina_id
    LEFT JOIN evento_oficinas eo1 ON eo1.evento_id = i.evento_id AND eo1.oficina_id = o1.id
    LEFT JOIN oficinas o2 ON o2.id = i.oficina_id_2
    LEFT JOIN evento_oficinas eo2 ON eo2.evento_id = i.evento_id AND eo2.oficina_id = o2.id
    WHERE i.id = p_inscricao_id;
$$;

GRANT EXECUTE ON FUNCTION public.get_inscricao_resumo(integer) TO anon, authenticated;
