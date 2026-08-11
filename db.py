"""
db.py — PostgreSQL connection handling and generic SQL execution helpers
for the Manhunt app.

This is the ONLY module that opens psycopg2 connections directly.
player_app.py and admin_app.py both build on top of the primitives here;
player_gui.py / admin_gui.py should only reach into this module for the
handful of lookups shared across both apps (e.g. populating dropdowns).

Edit the CONFIG dict below to match your database.
"""

from contextlib import contextmanager

import psycopg2

CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "manhunt",
    "user": "administrator",
    "password": "password",
}


def get_connection():
    """Open and return a new database connection."""
    return psycopg2.connect(**CONFIG)


@contextmanager
def get_cursor(commit: bool = False):
    """
    Open a connection + cursor, yield the cursor, and handle the
    commit/rollback/close lifecycle. Use this directly (instead of the
    run_* helpers below) when a single caller needs to issue multiple
    statements as one atomic transaction.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def run_query(sql, params=()):
    """
    Run a SELECT statement. Returns (columns, rows) where columns is a
    list of column-name strings and rows is a list of tuples — this
    shape is what feeds QTableWidget population directly in both GUIs.
    """
    with get_cursor(commit=False) as cur:
        cur.execute(sql, params)
        columns = [d[0] for d in cur.description]
        rows = cur.fetchall()
        return columns, rows


def run_command(sql, params=()):
    """Run an INSERT/UPDATE/DELETE with no RETURNING clause. Returns rowcount."""
    with get_cursor(commit=True) as cur:
        cur.execute(sql, params)
        return cur.rowcount


def run_command_returning(sql, params=()):
    """Run a single-row INSERT/UPDATE ... RETURNING statement. Returns the row tuple, or None."""
    with get_cursor(commit=True) as cur:
        cur.execute(sql, params)
        return cur.fetchone()


# ---------- Shared lookups (used by both player_app.py and admin_app.py) ----------

def get_player_by_id(player_id):
    """Return (player_id, username, email, display_name, avatar_url, created_at, is_banned) or None."""
    _, rows = run_query(
        """
        SELECT player_id, username, email, display_name, avatar_url, created_at, is_banned
        FROM player
        WHERE player_id = %s;
        """,
        (player_id,),
    )
    return rows[0] if rows else None


def get_player_by_username(username):
    """Return (player_id, username, email, display_name, avatar_url, created_at, is_banned) or None."""
    _, rows = run_query(
        """
        SELECT player_id, username, email, display_name, avatar_url, created_at, is_banned
        FROM player
        WHERE username = %s;
        """,
        (username,),
    )
    return rows[0] if rows else None


def list_game_builds():
    """
    Return (columns, rows) of all game builds. Used directly by
    player_gui.py's Transfer tab to populate the "host a game" build dropdown.
    """
    return run_query(
        """
        SELECT build_id, name, description, boundary_shrink_rate,
               initial_radius, final_radius, match_duration
        FROM game_build
        ORDER BY name;
        """
    )


def get_game_build(build_id):
    """Return a single game_build row tuple, or None."""
    _, rows = run_query(
        """
        SELECT build_id, name, description, boundary_shrink_rate,
               initial_radius, final_radius, match_duration
        FROM game_build
        WHERE build_id = %s;
        """,
        (build_id,),
    )
    return rows[0] if rows else None
