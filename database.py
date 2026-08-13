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
            evento_id INTEGER NOT NULL REFERENCES eventos(id) ON DELETE CASCADE,
            nome TEXT NOT NULL,
            preletor TEXT NOT NULL,
            vagas INTEGER NOT NULL
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
        "CREATE INDEX IF NOT EXISTS idx_oficinas_evento_id ON oficinas(evento_id)",
    ]

    with get_connection() as conn:
        cursor = conn.cursor()
        for statement in ddl_statements:
            cursor.execute(statement)


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
                evento_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                preletor TEXT NOT NULL,
                vagas INTEGER NOT NULL,
                FOREIGN KEY (evento_id) REFERENCES eventos(id) ON DELETE CASCADE
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
):
    with get_connection() as conn:
        cursor = conn.cursor()
        if uses_postgres():
            _execute(
                cursor,
                """
                INSERT INTO eventos (
                    nome, descricao, data_inicio, data_fim, inicio_inscricoes, fim_inscricoes,
                    banner_path, cor_primaria, cor_secundaria, ativo
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                ),
            )
            return _fetchone_dict(cursor)["id"]

        _execute(
            cursor,
            """
            INSERT INTO eventos (
                nome, descricao, data_inicio, data_fim, inicio_inscricoes, fim_inscricoes,
                banner_path, cor_primaria, cor_secundaria, ativo
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
):
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(
            cursor,
            """
            UPDATE eventos
            SET nome = %s, descricao = %s, data_inicio = %s, data_fim = %s,
                inicio_inscricoes = %s, fim_inscricoes = %s, banner_path = %s,
                cor_primaria = %s, cor_secundaria = %s, ativo = %s
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
                event_id,
            ),
        )


def delete_event(event_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(cursor, "DELETE FROM eventos WHERE id = %s", (event_id,))


# --- OPERAÇÕES DE OFICINAS ---

def create_workshop(evento_id, nome, preletor, vagas):
    with get_connection() as conn:
        cursor = conn.cursor()
        if uses_postgres():
            _execute(
                cursor,
                """
                INSERT INTO oficinas (evento_id, nome, preletor, vagas)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (evento_id, nome, preletor, vagas),
            )
            return _fetchone_dict(cursor)["id"]

        _execute(
            cursor,
            "INSERT INTO oficinas (evento_id, nome, preletor, vagas) VALUES (%s, %s, %s, %s)",
            (evento_id, nome, preletor, vagas),
        )
        return cursor.lastrowid


def get_workshops_by_event(evento_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(
            cursor,
            "SELECT * FROM oficinas WHERE evento_id = %s ORDER BY nome ASC",
            (evento_id,),
        )
        return _fetchall_dicts(cursor)


def get_workshop(workshop_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(cursor, "SELECT * FROM oficinas WHERE id = %s", (workshop_id,))
        return _fetchone_dict(cursor)


def delete_workshop(workshop_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(cursor, "DELETE FROM oficinas WHERE id = %s", (workshop_id,))


def update_workshop(workshop_id, nome, preletor, vagas):
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(
            cursor,
            "UPDATE oficinas SET nome = %s, preletor = %s, vagas = %s WHERE id = %s",
            (nome, preletor, vagas, workshop_id),
        )


def get_workshop_vagas_info(evento_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(
            cursor,
            """
            SELECT
                o.id,
                o.nome,
                o.preletor,
                o.vagas AS vagas_totais,
                (
                    SELECT COUNT(*) FROM inscricoes i
                    WHERE i.oficina_id = o.id OR i.oficina_id_2 = o.id
                ) AS vagas_ocupadas
            FROM oficinas o
            WHERE o.evento_id = %s
            ORDER BY o.nome ASC
            """,
            (evento_id,),
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


def _count_workshop_occupancy(cursor, oficina_id, exclude_registration_id=None):
    query = """
        SELECT COUNT(*) as ocupadas FROM inscricoes
        WHERE oficina_id = %s OR oficina_id_2 = %s
    """
    params = [oficina_id, oficina_id]
    if exclude_registration_id:
        query += " AND id != %s"
        params.append(exclude_registration_id)

    _execute(cursor, query, params)
    return _fetchone_dict(cursor)["ocupadas"]


def _has_workshop_vacancy(cursor, oficina_id, exclude_registration_id=None):
    _execute(cursor, "SELECT vagas FROM oficinas WHERE id = %s", (oficina_id,))
    row = _fetchone_dict(cursor)
    if not row:
        return False

    ocupadas = _count_workshop_occupancy(cursor, oficina_id, exclude_registration_id)
    return ocupadas < row["vagas"]


def _validate_workshop_selection(oficina_id, oficina_id_2):
    if oficina_id is not None and oficina_id_2 is not None and oficina_id == oficina_id_2:
        return False, "Selecione duas oficinas diferentes."
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

    if is_minor(data_nascimento):
        if not responsavel_nome or not responsavel_telefone:
            return False, "Menores de 18 anos devem informar nome e telefone do responsável.", None
    else:
        responsavel_nome = None
        responsavel_telefone = None

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

        selected_workshop_ids = [wid for wid in (oficina_id, oficina_id_2) if wid is not None]
        for workshop_id in selected_workshop_ids:
            if workshop_id in previous_workshop_ids:
                continue
            if not _has_workshop_vacancy(cursor, workshop_id, exclude_registration_id=exclude_id):
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
                o1.preletor AS oficina_preletor,
                o2.nome AS oficina_nome_2,
                o2.preletor AS oficina_preletor_2
            FROM inscricoes i
            LEFT JOIN oficinas o1 ON i.oficina_id = o1.id
            LEFT JOIN oficinas o2 ON i.oficina_id_2 = o2.id
            WHERE i.evento_id = %s
            ORDER BY i.data_inscricao DESC
            """,
            (evento_id,),
        )
        return _fetchall_dicts(cursor)


def delete_registration(registration_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        _execute(cursor, "DELETE FROM inscricoes WHERE id = %s", (registration_id,))


init_db()
