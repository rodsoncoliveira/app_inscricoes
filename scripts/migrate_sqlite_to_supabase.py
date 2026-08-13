"""
Copia dados do SQLite local (inscricoes.db) para o Supabase/PostgreSQL.

Uso:
  set DATABASE_URL=postgresql://...
  python scripts/migrate_sqlite_to_supabase.py
"""

import os
import sqlite3
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

SQLITE_PATH = os.path.join(ROOT_DIR, "inscricoes.db")


def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("Defina DATABASE_URL com a connection string do Supabase.")
        sys.exit(1)

    if not os.path.exists(SQLITE_PATH):
        print(f"Arquivo SQLite não encontrado: {SQLITE_PATH}")
        sys.exit(1)

    import psycopg2
    from psycopg2.extras import RealDictCursor

    import database as db

    db.init_db()

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    pg_conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    pg_cur = pg_conn.cursor()

    try:
        pg_cur.execute("SELECT COUNT(*) AS total FROM eventos")
        if pg_cur.fetchone()["total"] > 0:
            answer = input("O Supabase já possui eventos. Continuar mesmo assim? (s/N): ").strip().lower()
            if answer != "s":
                print("Migração cancelada.")
                return

        sqlite_cur.execute("SELECT * FROM eventos ORDER BY id")
        eventos = [dict(row) for row in sqlite_cur.fetchall()]
        evento_id_map = {}

        for evento in eventos:
            pg_cur.execute(
                """
                INSERT INTO eventos (
                    nome, descricao, data_inicio, data_fim, inicio_inscricoes, fim_inscricoes,
                    banner_path, cor_primaria, cor_secundaria, ativo
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    evento["nome"],
                    evento["descricao"],
                    evento["data_inicio"],
                    evento["data_fim"],
                    evento["inicio_inscricoes"],
                    evento["fim_inscricoes"],
                    evento["banner_path"],
                    evento["cor_primaria"],
                    evento["cor_secundaria"],
                    evento["ativo"],
                ),
            )
            evento_id_map[evento["id"]] = pg_cur.fetchone()["id"]

        sqlite_cur.execute("SELECT * FROM oficinas ORDER BY id")
        oficinas = [dict(row) for row in sqlite_cur.fetchall()]
        oficina_id_map = {}

        for oficina in oficinas:
            pg_cur.execute(
                """
                INSERT INTO oficinas (nome, preletor, ativo)
                VALUES (%s, %s, 1)
                RETURNING id
                """,
                (
                    oficina["nome"],
                    oficina["preletor"],
                ),
            )
            new_oficina_id = pg_cur.fetchone()["id"]
            oficina_id_map[oficina["id"]] = new_oficina_id
            pg_cur.execute(
                """
                INSERT INTO evento_oficinas (evento_id, oficina_id, vagas)
                VALUES (%s, %s, %s)
                ON CONFLICT (evento_id, oficina_id) DO NOTHING
                """,
                (
                    evento_id_map[oficina["evento_id"]],
                    new_oficina_id,
                    oficina["vagas"],
                ),
            )

        sqlite_cur.execute("SELECT * FROM inscricoes ORDER BY id")
        inscricoes = [dict(row) for row in sqlite_cur.fetchall()]

        for inscricao in inscricoes:
            pg_cur.execute(
                """
                INSERT INTO inscricoes (
                    evento_id, nome, data_nascimento, whatsapp, igreja,
                    responsavel_nome, responsavel_telefone, oficina_id, oficina_id_2, data_inscricao
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    evento_id_map[inscricao["evento_id"]],
                    inscricao["nome"],
                    inscricao["data_nascimento"],
                    inscricao["whatsapp"],
                    inscricao["igreja"],
                    inscricao.get("responsavel_nome"),
                    inscricao.get("responsavel_telefone"),
                    oficina_id_map.get(inscricao["oficina_id"]) if inscricao.get("oficina_id") else None,
                    oficina_id_map.get(inscricao["oficina_id_2"]) if inscricao.get("oficina_id_2") else None,
                    inscricao.get("data_inscricao"),
                ),
            )

        pg_conn.commit()
        print(
            f"Migração concluída: {len(eventos)} eventos, "
            f"{len(oficinas)} oficinas, {len(inscricoes)} inscrições."
        )
    except Exception as exc:
        pg_conn.rollback()
        print(f"Erro na migração: {exc}")
        sys.exit(1)
    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    main()
