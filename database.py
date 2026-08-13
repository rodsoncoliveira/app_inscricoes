import os
import re
import sqlite3
import unicodedata
from contextlib import contextmanager
from datetime import date, datetime
from difflib import SequenceMatcher

NAME_SIMILARITY_THRESHOLD = 0.88
SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inscricoes.db")


def coerce_to_date(value):
    """Converte valores vindos do SQLite (str) ou Postgres (date) para date."""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    return date.fromisoformat(str(value)[:10])


def format_date_br(value):
    """Formata data para exibição em pt-BR (dd/mm/aaaa)."""
    parsed = coerce_to_date(value)
    return parsed.strftime("%d/%m/%Y") if parsed else ""


def coerce_to_datetime(value):
    """Converte valores vindos do banco para datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, str):
        normalized = value.strip().replace("Z", "+00:00")
        if " " in normalized and "T" not in normalized:
            normalized = normalized.replace(" ", "T", 1)
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            parsed_date = coerce_to_date(normalized)
            return datetime.combine(parsed_date, datetime.min.time()) if parsed_date else None
    return coerce_to_datetime(str(value))


def format_datetime_br(value):
    """Formata data/hora para exibição em pt-BR (dd/mm/aaaa hh:mm:ss)."""
    parsed = coerce_to_datetime(value)
    if not parsed:
        return ""
    if parsed.tzinfo is not None:
        try:
            from zoneinfo import ZoneInfo

            parsed = parsed.astimezone(ZoneInfo("America/Sao_Paulo"))
        except Exception:
            parsed = parsed.replace(tzinfo=None)
    return parsed.strftime("%d/%m/%Y %H:%M:%S")


_use_postgres = None


def _read_streamlit_secrets():
    try:
        import streamlit as st

        return st.secrets
    except (ImportError, FileNotFoundError, AttributeError):
        return None


def _get_postgres_config():
    """
    Lê credenciais do Supabase/Postgres.

    Preferência:
    1. [database] com host/user/password (evita problemas com @, #, etc. na senha)
    2. DATABASE_URL ou database.url
    """
    secrets = _read_streamlit_secrets()
    if secrets:
        db_secrets = secrets.get("database")
        if db_secrets and db_secrets.get("host") and db_secrets.get("user") and db_secrets.get("password"):
            return {
                "host": db_secrets["host"],
                "port": int(db_secrets.get("port", 5432)),
                "user": db_secrets["user"],
                "password": db_secrets["password"],
                "dbname": db_secrets.get("dbname", "postgres"),
                "sslmode": db_secrets.get("sslmode", "require"),
            }

        if "DATABASE_URL" in secrets:
            return {"dsn": secrets["DATABASE_URL"]}

        if db_secrets and db_secrets.get("url"):
            return {"dsn": db_secrets["url"]}

    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return {"dsn": database_url}

    return None


def uses_postgres():
    global _use_postgres
    if _use_postgres is None:
        _use_postgres = _get_postgres_config() is not None
    return _use_postgres


def _connect_postgres():
    import psycopg2
    from psycopg2.extras import RealDictCursor

    config = _get_postgres_config()
    if not config:
        raise RuntimeError("Configuração do Postgres não encontrada.")

    connect_kwargs = {"cursor_factory": RealDictCursor}
    if "dsn" in config:
        connect_kwargs["dsn"] = config["dsn"]
    else:
        connect_kwargs.update(config)

    try:
        return psycopg2.connect(**connect_kwargs)
    except UnicodeDecodeError as exc:
        raise RuntimeError(
            "Falha ao conectar no Supabase. Se a senha tiver @, # ou %, "
            "use o bloco [database] no secrets.toml em vez de DATABASE_URL."
        ) from exc
    except Exception as exc:
        message = str(exc).strip() or repr(exc)
        raise RuntimeError(f"Falha ao conectar no Supabase: {message}") from exc


def _adapt_sql(sql):
    if uses_postgres():
        return sql
    return sql.replace("%s", "?")


def _row_to_dict(row):
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    return dict(row)


def _rows_to_dicts(rows):
    return [_row_to_dict(row) for row in rows]


@contextmanager
def get_connection():
    """Abre conexão com Supabase/Postgres ou SQLite local (fallback)."""
    if uses_postgres():
        conn = _connect_postgres()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def _execute(cursor, sql, params=()):
    cursor.execute(_adapt_sql(sql), params)


def _fetchone_dict(cursor):
    return _row_to_dict(cursor.fetchone())


def _fetchall_dicts(cursor):
    return _rows_to_dicts(cursor.fetchall())


def init_db():
    """Garante que as tabelas existam no banco configurado."""
    if uses_postgres():
        _init_postgres()
    else:
        _init_sqlite()


def _init_postgres():
    ddl_statements = [
        """
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
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS oficinas (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            preletor TEXT NOT NULL,
            descricao TEXT,
            ativo INTEGER DEFAULT 1
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS evento_oficinas (
            evento_id INTEGER NOT NULL REFERENCES eventos(id) ON DELETE CASCADE,
            oficina_id INTEGER NOT NULL REFERENCES oficinas(id) ON DELETE CASCADE,
            vagas INTEGER NOT NULL,
            preletor TEXT,
            PRIMARY KEY (evento_id, oficina_id)
        )
        """,
        """
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
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_inscricoes_evento_id ON inscricoes(evento_id)",
        "CREATE INDEX IF NOT EXISTS idx_inscricoes_evento_nascimento ON inscricoes(evento_id, data_nascimento)",
        "CREATE INDEX IF NOT EXISTS idx_evento_oficinas_evento ON evento_oficinas(evento_id)",
        "CREATE INDEX IF NOT EXISTS idx_evento_oficinas_oficina ON evento_oficinas(oficina_id)",
    ]

    with get_connection() as conn:
        cursor = conn.cursor()
        for statement in ddl_statements:
            cursor.execute(statement)
        _ensure_eventos_columns(cursor)
        _ensure_workshops_schema(cursor)


def _ensure_eventos_columns(cursor):
    """Garante colunas novas na tabela eventos sem recriar o banco."""
    if uses_postgres():
        cursor.execute("ALTER TABLE eventos ADD COLUMN IF NOT EXISTS whatsapp_grupo_url TEXT")
        return

    cursor.execute("PRAGMA table_info(eventos);")
    columns = [row["name"] for row in cursor.fetchall()]
    if "whatsapp_grupo_url" not in columns:
        cursor.execute("ALTER TABLE eventos ADD COLUMN whatsapp_grupo_url TEXT;")


def _table_has_column(cursor, table_name, column_name):
    if uses_postgres():
        _execute(
            cursor,
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
            """,
            (table_name, column_name),
        )
        return cursor.fetchone() is not None

    _execute(cursor, f"PRAGMA table_info({table_name});")
    return any(row["name"] == column_name for row in cursor.fetchall())


def _ensure_workshops_schema(cursor):
    """Migra oficinas acopladas ao evento para catálogo + evento_oficinas."""
    if uses_postgres():
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS evento_oficinas (
                evento_id INTEGER NOT NULL REFERENCES eventos(id) ON DELETE CASCADE,
                oficina_id INTEGER NOT NULL REFERENCES oficinas(id) ON DELETE CASCADE,
                vagas INTEGER NOT NULL,
                preletor TEXT,
                PRIMARY KEY (evento_id, oficina_id)
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_evento_oficinas_evento ON evento_oficinas(evento_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_evento_oficinas_oficina ON evento_oficinas(oficina_id)")
        cursor.execute("ALTER TABLE oficinas ADD COLUMN IF NOT EXISTS descricao TEXT")
        cursor.execute("ALTER TABLE oficinas ADD COLUMN IF NOT EXISTS ativo INTEGER DEFAULT 1")

        if _table_has_column(cursor, "oficinas", "evento_id"):
            cursor.execute(
                """
                INSERT INTO evento_oficinas (evento_id, oficina_id, vagas)
                SELECT evento_id, id, vagas
                FROM oficinas
                WHERE evento_id IS NOT NULL
                ON CONFLICT (evento_id, oficina_id) DO NOTHING
                """
            )
            cursor.execute("ALTER TABLE oficinas DROP COLUMN evento_id")
            cursor.execute("ALTER TABLE oficinas DROP COLUMN vagas")
        return

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS evento_oficinas (
            evento_id INTEGER NOT NULL,
            oficina_id INTEGER NOT NULL,
            vagas INTEGER NOT NULL,
            preletor TEXT,
            PRIMARY KEY (evento_id, oficina_id),
            FOREIGN KEY (evento_id) REFERENCES eventos(id) ON DELETE CASCADE,
            FOREIGN KEY (oficina_id) REFERENCES oficinas(id) ON DELETE CASCADE
        )
        """
    )

    if not _table_has_column(cursor, "oficinas", "evento_id"):
        if not _table_has_column(cursor, "oficinas", "descricao"):
            cursor.execute("ALTER TABLE oficinas ADD COLUMN descricao TEXT;")
        if not _table_has_column(cursor, "oficinas", "ativo"):
            cursor.execute("ALTER TABLE oficinas ADD COLUMN ativo INTEGER DEFAULT 1;")
        return

    cursor.execute(
        """
        INSERT OR IGNORE INTO evento_oficinas (evento_id, oficina_id, vagas)
        SELECT evento_id, id, vagas FROM oficinas WHERE evento_id IS NOT NULL
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS oficinas_catalog (
            id INTEGER PRIMARY KEY,
            nome TEXT NOT NULL,
            preletor TEXT NOT NULL,
            descricao TEXT,
            ativo INTEGER DEFAULT 1
        )
        """
    )
    cursor.execute(
        """
        INSERT OR IGNORE INTO oficinas_catalog (id, nome, preletor, ativo)
        SELECT id, nome, preletor, 1 FROM oficinas
        """
    )
    cursor.execute("DROP TABLE oficinas")
    cursor.execute("ALTER TABLE oficinas_catalog RENAME TO oficinas")


def _init_sqlite():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        cursor.execute("PRAGMA table_info(eventos);")
        columns = [row["name"] for row in cursor.fetchall()]
        if len(columns) > 0 and "data_evento" in columns:
            cursor.execute("DROP TABLE IF EXISTS inscricoes;")
            cursor.execute("DROP TABLE IF EXISTS oficinas;")
            cursor.execute("DROP TABLE IF EXISTS eventos;")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS oficinas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                preletor TEXT NOT NULL,
                descricao TEXT,
                ativo INTEGER DEFAULT 1
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS evento_oficinas (
                evento_id INTEGER NOT NULL,
                oficina_id INTEGER NOT NULL,
                vagas INTEGER NOT NULL,
                preletor TEXT,
                PRIMARY KEY (evento_id, oficina_id),
                FOREIGN KEY (evento_id) REFERENCES eventos(id) ON DELETE CASCADE,
                FOREIGN KEY (oficina_id) REFERENCES oficinas(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS inscricoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evento_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                data_nascimento DATE NOT NULL,
                whatsapp TEXT NOT NULL,
                igreja TEXT NOT NULL,
                responsavel_nome TEXT,
                responsavel_telefone TEXT,
                oficina_id INTEGER,
                oficina_id_2 INTEGER,
                data_inscricao DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (evento_id) REFERENCES eventos(id) ON DELETE CASCADE,
                FOREIGN KEY (oficina_id) REFERENCES oficinas(id) ON DELETE SET NULL,
                FOREIGN KEY (oficina_id_2) REFERENCES oficinas(id) ON DELETE SET NULL
            )
            """
        )

        cursor.execute("PRAGMA table_info(inscricoes);")
        inscricoes_columns = [row["name"] for row in cursor.fetchall()]
        if "oficina_id_2" not in inscricoes_columns:
            cursor.execute("ALTER TABLE inscricoes ADD COLUMN oficina_id_2 INTEGER;")
        if "responsavel_nome" not in inscricoes_columns:
            cursor.execute("ALTER TABLE inscricoes ADD COLUMN responsavel_nome TEXT;")
        if "responsavel_telefone" not in inscricoes_columns:
            cursor.execute("ALTER TABLE inscricoes ADD COLUMN responsavel_telefone TEXT;")

        cursor.execute("DROP INDEX IF EXISTS idx_inscricoes_evento_cpf")
        if "cpf" in inscricoes_columns:
            try:
                cursor.execute("ALTER TABLE inscricoes DROP COLUMN cpf")
            except sqlite3.OperationalError:
                pass

        _ensure_eventos_columns(cursor)
        _ensure_workshops_schema(cursor)


def normalize_whatsapp_group_url(url):
    """Normaliza link de convite do grupo WhatsApp."""
    if not url:
        return ""
    normalized = str(url).strip()
    if not normalized:
        return ""
    if normalized.startswith("www."):
        normalized = f"https://{normalized}"
    if not normalized.startswith(("http://", "https://")):
        if "chat.whatsapp.com" in normalized:
            normalized = f"https://{normalized}"
    return normalized


# --- OPERAÇÕES DE EVENTOS ---

def create_event(
    nome,
    descricao,
    data_inicio,
    data_fim,
    inicio_inscricoes,
    fim_inscricoes,
    banner_path,
    cor_primaria,
    cor_secundaria,
    ativo=1,
    whatsapp_grupo_url=None,
):
    whatsapp_grupo_url = normalize_whatsapp_group_url(whatsapp_grupo_url) or None
    with get_connection() as conn:
        cursor = conn.cursor()
        if uses_postgres():
            _execute(
                cursor,
                """
                INSERT INTO eventos (
                    nome, descricao, data_inicio, data_fim, inicio_inscricoes, fim_inscricoes,
                    banner_path, cor_primaria, cor_secundaria, ativo, whatsapp_grupo_url
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    nome,
                    descricao,
                    data_inicio,
                    data_fim,
                    inicio_inscricoes,
                    fim_inscricoes,
                    banner_path,
                    cor_primaria,
                    cor_secundaria,
                    ativo,
                    whatsapp_grupo_url,
                ),
            )
            return _fetchone_dict(cursor)["id"]

        _execute(
            cursor,
            """
            INSERT INTO eventos (
                nome, descricao, data_inicio, data_fim, inicio_inscricoes, fim_inscricoes,
                banner_path, cor_primaria, cor_secundaria, ativo, whatsapp_grupo_url
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                nome,
                descricao,
                data_inicio,
                data_fim,
                inicio_inscricoes,
                fim_inscricoes,
                banner_path,
                cor_primaria,
                cor_secundaria,
                ativo,
                whatsapp_grupo_url,
            ),
        )
        return cursor.lastrowid


def get_all_events():
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(cursor, "SELECT * FROM eventos ORDER BY data_inicio DESC")
        return _fetchall_dicts(cursor)


def get_active_events():
    today = date.today().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(
            cursor,
            """
            SELECT * FROM eventos
            WHERE ativo = 1 AND inicio_inscricoes <= %s AND fim_inscricoes >= %s
            ORDER BY data_inicio ASC
            """,
            (today, today),
        )
        return _fetchall_dicts(cursor)


def validate_event_dates(data_inicio, data_fim, inicio_inscricoes, fim_inscricoes):
    errors = []
    if data_inicio > data_fim:
        errors.append("A data de fim do evento deve ser igual ou posterior à data de início.")
    if inicio_inscricoes > fim_inscricoes:
        errors.append("O fim das inscrições deve ser igual ou posterior ao início das inscrições.")
    return errors


def get_registration_visibility(event):
    if event.get("ativo", 0) != 1:
        return False, "Evento inativo"

    try:
        inicio = coerce_to_date(event["inicio_inscricoes"])
        fim = coerce_to_date(event["fim_inscricoes"])
    except (TypeError, ValueError):
        return False, "Datas de inscrição inválidas"

    if inicio > fim:
        return False, "Período de inscrições inconsistente"

    today = date.today()
    if today < inicio:
        return False, f"Inscrições abrem em {inicio.strftime('%d/%m/%Y')}"
    if today > fim:
        return False, f"Inscrições encerradas em {fim.strftime('%d/%m/%Y')}"

    return True, "Visível no portal"


def get_event(event_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(cursor, "SELECT * FROM eventos WHERE id = %s", (event_id,))
        return _fetchone_dict(cursor)


def update_event(
    event_id,
    nome,
    descricao,
    data_inicio,
    data_fim,
    inicio_inscricoes,
    fim_inscricoes,
    banner_path,
    cor_primaria,
    cor_secundaria,
    ativo,
    whatsapp_grupo_url=None,
):
    whatsapp_grupo_url = normalize_whatsapp_group_url(whatsapp_grupo_url) or None
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(
            cursor,
            """
            UPDATE eventos
            SET nome = %s, descricao = %s, data_inicio = %s, data_fim = %s,
                inicio_inscricoes = %s, fim_inscricoes = %s, banner_path = %s,
                cor_primaria = %s, cor_secundaria = %s, ativo = %s, whatsapp_grupo_url = %s
            WHERE id = %s
            """,
            (
                nome,
                descricao,
                data_inicio,
                data_fim,
                inicio_inscricoes,
                fim_inscricoes,
                banner_path,
                cor_primaria,
                cor_secundaria,
                ativo,
                whatsapp_grupo_url,
                event_id,
            ),
        )


def delete_event(event_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(cursor, "DELETE FROM eventos WHERE id = %s", (event_id,))


# --- OPERAÇÕES DE OFICINAS ---

def create_workshop_catalog(nome, preletor, descricao=None, ativo=1):
    with get_connection() as conn:
        cursor = conn.cursor()
        if uses_postgres():
            _execute(
                cursor,
                """
                INSERT INTO oficinas (nome, preletor, descricao, ativo)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (nome, preletor, descricao, ativo),
            )
            return _fetchone_dict(cursor)["id"]

        _execute(
            cursor,
            "INSERT INTO oficinas (nome, preletor, descricao, ativo) VALUES (%s, %s, %s, %s)",
            (nome, preletor, descricao, ativo),
        )
        return cursor.lastrowid


def create_workshop(evento_id, nome, preletor, vagas):
    """Cria oficina no catálogo e vincula ao evento."""
    workshop_id = create_workshop_catalog(nome, preletor)
    link_workshop_to_event(evento_id, workshop_id, vagas)
    return workshop_id


def get_all_workshops():
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(cursor, "SELECT * FROM oficinas ORDER BY nome ASC")
        return _fetchall_dicts(cursor)


def get_workshops_by_event(evento_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(
            cursor,
            """
            SELECT
                o.id,
                o.nome,
                COALESCE(eo.preletor, o.preletor) AS preletor,
                o.descricao,
                o.ativo,
                eo.vagas,
                eo.evento_id
            FROM evento_oficinas eo
            JOIN oficinas o ON o.id = eo.oficina_id
            WHERE eo.evento_id = %s
            ORDER BY o.nome ASC
            """,
            (evento_id,),
        )
        return _fetchall_dicts(cursor)


def get_workshop(workshop_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(cursor, "SELECT * FROM oficinas WHERE id = %s", (workshop_id,))
        return _fetchone_dict(cursor)


def get_workshop_event_link(evento_id, workshop_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(
            cursor,
            """
            SELECT
                eo.evento_id,
                eo.oficina_id,
                eo.vagas,
                eo.preletor AS preletor_evento,
                o.nome,
                o.preletor AS preletor_catalogo
            FROM evento_oficinas eo
            JOIN oficinas o ON o.id = eo.oficina_id
            WHERE eo.evento_id = %s AND eo.oficina_id = %s
            """,
            (evento_id, workshop_id),
        )
        return _fetchone_dict(cursor)


def link_workshop_to_event(evento_id, oficina_id, vagas, preletor=None):
    preletor = preletor.strip() if preletor else None
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(
            cursor,
            """
            INSERT INTO evento_oficinas (evento_id, oficina_id, vagas, preletor)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (evento_id, oficina_id) DO UPDATE
            SET vagas = EXCLUDED.vagas,
                preletor = EXCLUDED.preletor
            """,
            (evento_id, oficina_id, vagas, preletor),
        )


def unlink_workshop_from_event(evento_id, oficina_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(
            cursor,
            "DELETE FROM evento_oficinas WHERE evento_id = %s AND oficina_id = %s",
            (evento_id, oficina_id),
        )


def delete_workshop(workshop_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(cursor, "DELETE FROM oficinas WHERE id = %s", (workshop_id,))


def update_workshop(workshop_id, nome, preletor, descricao=None, ativo=1):
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(
            cursor,
            """
            UPDATE oficinas
            SET nome = %s, preletor = %s, descricao = %s, ativo = %s
            WHERE id = %s
            """,
            (nome, preletor, descricao, ativo, workshop_id),
        )


def update_event_workshop_link(evento_id, oficina_id, vagas, preletor=None):
    preletor = preletor.strip() if preletor else None
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(
            cursor,
            """
            UPDATE evento_oficinas
            SET vagas = %s, preletor = %s
            WHERE evento_id = %s AND oficina_id = %s
            """,
            (vagas, preletor, evento_id, oficina_id),
        )


def get_workshop_event_links(oficina_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(
            cursor,
            """
            SELECT e.id, e.nome, eo.vagas
            FROM evento_oficinas eo
            JOIN eventos e ON e.id = eo.evento_id
            WHERE eo.oficina_id = %s
            ORDER BY e.data_inicio DESC
            """,
            (oficina_id,),
        )
        return _fetchall_dicts(cursor)


def get_workshop_vagas_info(evento_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(
            cursor,
            """
            SELECT
                o.id,
                o.nome,
                COALESCE(eo.preletor, o.preletor) AS preletor,
                eo.vagas AS vagas_totais,
                (
                    SELECT COUNT(*) FROM inscricoes i
                    WHERE i.evento_id = %s
                      AND (i.oficina_id = o.id OR i.oficina_id_2 = o.id)
                ) AS vagas_ocupadas
            FROM evento_oficinas eo
            JOIN oficinas o ON o.id = eo.oficina_id
            WHERE eo.evento_id = %s
            ORDER BY o.nome ASC
            """,
            (evento_id, evento_id),
        )
        rows = _fetchall_dicts(cursor)

    result = []
    for row in rows:
        row["vagas_restantes"] = max(0, row["vagas_totais"] - row["vagas_ocupadas"])
        result.append(row)
    return result


# --- OPERAÇÕES DE INSCRIÇÕES ---

def normalize_name(name):
    if not name:
        return ""

    normalized = unicodedata.normalize("NFD", name.strip().lower())
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def name_similarity(name_a, name_b):
    norm_a = normalize_name(name_a)
    norm_b = normalize_name(name_b)
    if not norm_a or not norm_b:
        return 0.0
    if norm_a == norm_b:
        return 1.0
    return SequenceMatcher(None, norm_a, norm_b).ratio()


def find_matching_registration(evento_id, nome, data_nascimento):
    if isinstance(data_nascimento, date):
        data_nasc_str = data_nascimento.isoformat()
    else:
        data_nasc_str = data_nascimento

    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(
            cursor,
            "SELECT * FROM inscricoes WHERE evento_id = %s AND data_nascimento = %s",
            (evento_id, data_nasc_str),
        )
        rows = _fetchall_dicts(cursor)

    best_match = None
    best_score = 0.0
    for row in rows:
        score = name_similarity(nome, row["nome"])
        if score > best_score:
            best_score = score
            best_match = row

    if best_match and best_score >= NAME_SIMILARITY_THRESHOLD:
        return best_match

    return None


def is_minor(data_nascimento):
    if isinstance(data_nascimento, str):
        data_nascimento = date.fromisoformat(data_nascimento)

    today = date.today()
    age = today.year - data_nascimento.year
    if (today.month, today.day) < (data_nascimento.month, data_nascimento.day):
        age -= 1
    return age < 18


def validate_guardian_fields(data_nascimento, responsavel_nome, responsavel_telefone):
    """Valida dados do responsável quando o participante é menor de idade."""
    nome = responsavel_nome.strip() if responsavel_nome else ""
    telefone = responsavel_telefone.strip() if responsavel_telefone else ""

    if is_minor(data_nascimento):
        if not nome or not telefone:
            return False, "Menores de 18 anos devem informar nome e telefone do responsável.", None, None
        return True, "", nome, telefone

    return True, "", None, None


def _count_workshop_occupancy(cursor, oficina_id, evento_id, exclude_registration_id=None):
    query = """
        SELECT COUNT(*) as ocupadas FROM inscricoes
        WHERE evento_id = %s AND (oficina_id = %s OR oficina_id_2 = %s)
    """
    params = [evento_id, oficina_id, oficina_id]
    if exclude_registration_id:
        query += " AND id != %s"
        params.append(exclude_registration_id)

    _execute(cursor, query, params)
    return _fetchone_dict(cursor)["ocupadas"]


def _has_workshop_vacancy(cursor, oficina_id, evento_id, exclude_registration_id=None):
    _execute(
        cursor,
        "SELECT vagas FROM evento_oficinas WHERE evento_id = %s AND oficina_id = %s",
        (evento_id, oficina_id),
    )
    row = _fetchone_dict(cursor)
    if not row:
        return False

    ocupadas = _count_workshop_occupancy(cursor, oficina_id, evento_id, exclude_registration_id)
    return ocupadas < row["vagas"]


def _validate_workshop_selection(oficina_id, oficina_id_2):
    if oficina_id is not None and oficina_id_2 is not None and oficina_id == oficina_id_2:
        return False, "Selecione duas oficinas diferentes."
    return True, ""


def _validate_workshops_for_event(cursor, evento_id, oficina_id, oficina_id_2):
    for workshop_id in (oficina_id, oficina_id_2):
        if workshop_id is None:
            continue
        _execute(
            cursor,
            """
            SELECT 1 FROM evento_oficinas
            WHERE evento_id = %s AND oficina_id = %s
            """,
            (evento_id, workshop_id),
        )
        if not _fetchone_dict(cursor):
            workshop_name = _get_workshop_name(cursor, workshop_id)
            return False, f"A oficina '{workshop_name}' não está disponível neste evento."
    return True, ""


def _get_workshop_name(cursor, oficina_id):
    _execute(cursor, "SELECT nome FROM oficinas WHERE id = %s", (oficina_id,))
    row = _fetchone_dict(cursor)
    return row["nome"] if row else "Oficina"


def create_registration(
    evento_id,
    nome,
    data_nascimento,
    whatsapp,
    igreja,
    oficina_id,
    oficina_id_2=None,
    responsavel_nome=None,
    responsavel_telefone=None,
):
    nome = nome.strip()
    if not nome:
        return False, "Informe o nome completo do participante.", None

    if isinstance(data_nascimento, date):
        data_nascimento = data_nascimento.isoformat()

    guardian_ok, guardian_error, responsavel_nome, responsavel_telefone = validate_guardian_fields(
        data_nascimento,
        responsavel_nome,
        responsavel_telefone,
    )
    if not guardian_ok:
        return False, guardian_error, None

    valid_selection, selection_error = _validate_workshop_selection(oficina_id, oficina_id_2)
    if not valid_selection:
        return False, selection_error, None

    existing = find_matching_registration(evento_id, nome, data_nascimento)
    exclude_id = existing["id"] if existing else None
    previous_workshop_ids = set()
    if existing:
        if existing.get("oficina_id"):
            previous_workshop_ids.add(existing["oficina_id"])
        if existing.get("oficina_id_2"):
            previous_workshop_ids.add(existing["oficina_id_2"])

    with get_connection() as conn:
        cursor = conn.cursor()

        event_valid, event_error = _validate_workshops_for_event(
            cursor, evento_id, oficina_id, oficina_id_2
        )
        if not event_valid:
            return False, event_error, None

        selected_workshop_ids = [wid for wid in (oficina_id, oficina_id_2) if wid is not None]
        for workshop_id in selected_workshop_ids:
            if workshop_id in previous_workshop_ids:
                continue
            if not _has_workshop_vacancy(cursor, workshop_id, evento_id, exclude_registration_id=exclude_id):
                workshop_name = _get_workshop_name(cursor, workshop_id)
                return False, f"A oficina '{workshop_name}' já está lotada! Por favor, escolha outra.", None

        if existing:
            if uses_postgres():
                _execute(
                    cursor,
                    """
                    UPDATE inscricoes
                    SET nome = %s, data_nascimento = %s, whatsapp = %s, igreja = %s,
                        responsavel_nome = %s, responsavel_telefone = %s,
                        oficina_id = %s, oficina_id_2 = %s, data_inscricao = NOW()
                    WHERE id = %s
                    """,
                    (
                        nome,
                        data_nascimento,
                        whatsapp,
                        igreja,
                        responsavel_nome,
                        responsavel_telefone,
                        oficina_id,
                        oficina_id_2,
                        existing["id"],
                    ),
                )
            else:
                _execute(
                    cursor,
                    """
                    UPDATE inscricoes
                    SET nome = %s, data_nascimento = %s, whatsapp = %s, igreja = %s,
                        responsavel_nome = %s, responsavel_telefone = %s,
                        oficina_id = %s, oficina_id_2 = %s, data_inscricao = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (
                        nome,
                        data_nascimento,
                        whatsapp,
                        igreja,
                        responsavel_nome,
                        responsavel_telefone,
                        oficina_id,
                        oficina_id_2,
                        existing["id"],
                    ),
                )
            return True, existing["id"], "updated"

        if uses_postgres():
            _execute(
                cursor,
                """
                INSERT INTO inscricoes (
                    evento_id, nome, data_nascimento, whatsapp, igreja,
                    responsavel_nome, responsavel_telefone, oficina_id, oficina_id_2
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    evento_id,
                    nome,
                    data_nascimento,
                    whatsapp,
                    igreja,
                    responsavel_nome,
                    responsavel_telefone,
                    oficina_id,
                    oficina_id_2,
                ),
            )
            inscricao_id = _fetchone_dict(cursor)["id"]
        else:
            _execute(
                cursor,
                """
                INSERT INTO inscricoes (
                    evento_id, nome, data_nascimento, whatsapp, igreja,
                    responsavel_nome, responsavel_telefone, oficina_id, oficina_id_2
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    evento_id,
                    nome,
                    data_nascimento,
                    whatsapp,
                    igreja,
                    responsavel_nome,
                    responsavel_telefone,
                    oficina_id,
                    oficina_id_2,
                ),
            )
            inscricao_id = cursor.lastrowid

    return True, inscricao_id, "created"


def get_registrations_by_event(evento_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(
            cursor,
            """
            SELECT
                i.id,
                i.nome,
                i.data_nascimento,
                i.whatsapp,
                i.igreja,
                i.responsavel_nome,
                i.responsavel_telefone,
                i.data_inscricao,
                o1.nome AS oficina_nome,
                COALESCE(eo1.preletor, o1.preletor) AS oficina_preletor,
                o2.nome AS oficina_nome_2,
                COALESCE(eo2.preletor, o2.preletor) AS oficina_preletor_2
            FROM inscricoes i
            LEFT JOIN oficinas o1 ON i.oficina_id = o1.id
            LEFT JOIN evento_oficinas eo1 ON eo1.evento_id = i.evento_id AND eo1.oficina_id = o1.id
            LEFT JOIN oficinas o2 ON i.oficina_id_2 = o2.id
            LEFT JOIN evento_oficinas eo2 ON eo2.evento_id = i.evento_id AND eo2.oficina_id = o2.id
            WHERE i.evento_id = %s
            ORDER BY i.data_inscricao DESC
            """,
            (evento_id,),
        )
        return _fetchall_dicts(cursor)


def get_registration(registration_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(
            cursor,
            """
            SELECT
                i.id,
                i.evento_id,
                i.nome,
                i.data_nascimento,
                i.whatsapp,
                i.igreja,
                i.responsavel_nome,
                i.responsavel_telefone,
                i.oficina_id,
                i.oficina_id_2,
                i.data_inscricao,
                e.nome AS evento_nome,
                o1.nome AS oficina_nome,
                COALESCE(eo1.preletor, o1.preletor) AS oficina_preletor,
                o2.nome AS oficina_nome_2,
                COALESCE(eo2.preletor, o2.preletor) AS oficina_preletor_2
            FROM inscricoes i
            JOIN eventos e ON i.evento_id = e.id
            LEFT JOIN oficinas o1 ON i.oficina_id = o1.id
            LEFT JOIN evento_oficinas eo1 ON eo1.evento_id = i.evento_id AND eo1.oficina_id = o1.id
            LEFT JOIN oficinas o2 ON i.oficina_id_2 = o2.id
            LEFT JOIN evento_oficinas eo2 ON eo2.evento_id = i.evento_id AND eo2.oficina_id = o2.id
            WHERE i.id = %s
            """,
            (registration_id,),
        )
        return _fetchone_dict(cursor)


def update_registration_workshops(registration_id, oficina_id, oficina_id_2=None):
    """Atualiza apenas as oficinas escolhidas após a inscrição inicial."""
    valid_selection, selection_error = _validate_workshop_selection(oficina_id, oficina_id_2)
    if not valid_selection:
        return False, selection_error

    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(
            cursor,
            "SELECT evento_id, oficina_id, oficina_id_2 FROM inscricoes WHERE id = %s",
            (registration_id,),
        )
        row = _fetchone_dict(cursor)
        if not row:
            return False, "Inscrição não encontrada."

        evento_id = row["evento_id"]
        event_valid, event_error = _validate_workshops_for_event(
            cursor, evento_id, oficina_id, oficina_id_2
        )
        if not event_valid:
            return False, event_error

        previous_workshop_ids = set()
        if row.get("oficina_id"):
            previous_workshop_ids.add(row["oficina_id"])
        if row.get("oficina_id_2"):
            previous_workshop_ids.add(row["oficina_id_2"])

        selected_workshop_ids = [wid for wid in (oficina_id, oficina_id_2) if wid is not None]
        for workshop_id in selected_workshop_ids:
            if workshop_id in previous_workshop_ids:
                continue
            if not _has_workshop_vacancy(
                cursor, workshop_id, evento_id, exclude_registration_id=registration_id
            ):
                workshop_name = _get_workshop_name(cursor, workshop_id)
                return False, f"A oficina '{workshop_name}' já está lotada! Por favor, escolha outra."

        _execute(
            cursor,
            "UPDATE inscricoes SET oficina_id = %s, oficina_id_2 = %s WHERE id = %s",
            (oficina_id, oficina_id_2, registration_id),
        )

    return True, registration_id


def delete_registration(registration_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(cursor, "DELETE FROM inscricoes WHERE id = %s", (registration_id,))


init_db()
