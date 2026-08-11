import db

# ===================================================== #
#                      Query & Search                   #
# ===================================================== #

def search_players(username_substr=None, is_banned=None):
    """(columns, rows) of players matching the given optional filters."""
    clauses = []
    params = []
    if username_substr:
        clauses.append("username ILIKE %s")
        params.append(f"%{username_substr}%")
    if is_banned is not None:
        clauses.append("is_banned = %s")
        params.append(is_banned)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT player_id, username, email, display_name, avatar_url, created_at, is_banned
        FROM player
        {where}
        ORDER BY player_id;
    """
    return db.run_query(sql, tuple(params))


def search_games(date_from=None, date_to=None, status=None, winning_side=None,
                  min_players=None, max_players=None):
    """(columns, rows) of games matching the given optional filters."""
    where_clauses = []
    where_params = []
    if date_from is not None:
        where_clauses.append("g.started_at >= %s")
        where_params.append(date_from)
    if date_to is not None:
        where_clauses.append("g.started_at <= %s")
        where_params.append(date_to)
    if status:
        where_clauses.append("g.status = %s")
        where_params.append(status)
    if winning_side:
        where_clauses.append("g.winning_side = %s")
        where_params.append(winning_side)

    having_clauses = []
    having_params = []
    if min_players is not None:
        having_clauses.append("COUNT(gp.player_id) >= %s")
        having_params.append(min_players)
    if max_players is not None:
        having_clauses.append("COUNT(gp.player_id) <= %s")
        having_params.append(max_players)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    having_sql = f"HAVING {' AND '.join(having_clauses)}" if having_clauses else ""

    sql = f"""
        SELECT g.game_id, g.invite_code, g.status, g.center_lat, g.center_lng,
               g.started_at, g.ended_at, g.winning_side, gb.name AS build_name,
               host.username AS host_username,
               COUNT(gp.player_id) AS participant_count
        FROM game g
        JOIN game_build gb ON gb.build_id = g.build_id
        JOIN player host ON host.player_id = g.player_id
        LEFT JOIN game_participant gp ON gp.game_id = g.game_id
        {where_sql}
        GROUP BY g.game_id, gb.name, host.username
        {having_sql}
        ORDER BY g.game_id DESC;
    """
    return db.run_query(sql, tuple(where_params + having_params))

# ===================================================== #
#                      Manage Players                   #
# ===================================================== #

def list_all_players():
    """(columns, rows) of all players — feeds the Manage Players tab's right-side table."""
    return db.run_query(
        """
        SELECT player_id, username, email, display_name, avatar_url, created_at, is_banned
        FROM player
        ORDER BY player_id;
        """
    )


def ban_player(player_id):
    return db.run_command("UPDATE player SET is_banned = true WHERE player_id = %s;", (player_id,))


def unban_player(player_id):
    return db.run_command("UPDATE player SET is_banned = false WHERE player_id = %s;", (player_id,))


def create_player(username, email, display_name=None, avatar_url=None):
    """Admin-side player creation. Returns the new player_id. Raises on duplicate username/email."""
    row = db.run_command_returning(
        """
        INSERT INTO player (username, email, display_name, avatar_url)
        VALUES (%s, %s, %s, %s)
        RETURNING player_id;
        """,
        (username, email, display_name, avatar_url),
    )
    return row[0]


def delete_player(player_id):
    return db.run_command("DELETE FROM player WHERE player_id = %s;", (player_id,))

# ===================================================== #
#                      Leaderboard / Reports            #
# ===================================================== #

def report_top_taggers(limit=20):
    return db.run_query(
        """
        SELECT p.player_id, p.username, COUNT(*) AS tags_landed
        FROM game_event ge
        JOIN player p ON p.player_id = ge.player_id
        WHERE ge.event_type_code = 'TAG'
        GROUP BY p.player_id, p.username
        ORDER BY tags_landed DESC
        LIMIT %s;
        """,
        (limit,),
    )


def report_survival_rate(limit=20):
    return db.run_query(
        """
        SELECT p.player_id, p.username,
               COUNT(*) FILTER (WHERE gp.survived = true) AS games_survived,
               COUNT(*) AS games_played,
               ROUND(100.0 * COUNT(*) FILTER (WHERE gp.survived = true) / NULLIF(COUNT(*), 0), 1) AS survival_rate_pct
        FROM game_participant gp
        JOIN player p ON p.player_id = gp.player_id
        WHERE gp.survived IS NOT NULL
        GROUP BY p.player_id, p.username
        ORDER BY survival_rate_pct DESC
        LIMIT %s;
        """,
        (limit,),
    )


def report_most_wins(limit=20):
    return db.run_query(
        """
        SELECT p.player_id, p.username, COUNT(*) AS wins
        FROM game_participant gp
        JOIN game g ON g.game_id = gp.game_id
        JOIN player p ON p.player_id = gp.player_id
        WHERE g.status = 'completed'
          AND g.winning_side = (CASE gp.final_role
                                     WHEN 'hunter' THEN 'hunters'
                                     WHEN 'hider' THEN 'hiders'
                                 END)::game_side
        GROUP BY p.player_id, p.username
        ORDER BY wins DESC
        LIMIT %s;
        """,
        (limit,),
    )


def report_avg_match_duration(limit=None):
    return db.run_query(
        """
        SELECT COUNT(*) AS completed_games,
               ROUND(AVG(EXTRACT(EPOCH FROM (ended_at - started_at)))::numeric, 1) AS avg_duration_sec
        FROM game
        WHERE status = 'completed' AND started_at IS NOT NULL AND ended_at IS NOT NULL;
        """
    )


def report_common_power_ups(limit=20):
    return db.run_query(
        """
        SELECT pu.power_up_id, pu.name, pu.effect_type, COUNT(*) AS times_used
        FROM game_event ge
        JOIN power_up pu ON pu.power_up_id = ge.power_up_id
        WHERE ge.event_type_code = 'POWER_UP_USE'
        GROUP BY pu.power_up_id, pu.name, pu.effect_type
        ORDER BY times_used DESC
        LIMIT %s;
        """,
        (limit,),
    )


def report_avg_players_per_match(limit=None):
    return db.run_query(
        """
        SELECT ROUND(AVG(participant_count)::numeric, 2) AS avg_players_per_match
        FROM (
            SELECT game_id, COUNT(*) AS participant_count
            FROM game_participant
            GROUP BY game_id
        ) sub;
        """
    )


def report_win_rate_by_side(limit=None):
    return db.run_query(
        """
        SELECT winning_side, COUNT(*) AS wins,
               ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS win_pct
        FROM game
        WHERE status = 'completed' AND winning_side IS NOT NULL
        GROUP BY winning_side;
        """
    )


# key -> (display label, report function)
REPORTS = {
    "top_taggers": ("Top Taggers", report_top_taggers),
    "survival_rate": ("Survival Rate Leaderboard", report_survival_rate),
    "most_wins": ("Most Games Won", report_most_wins),
    "avg_match_duration": ("Average Match Duration", report_avg_match_duration),
    "common_power_ups": ("Most Commonly Used Power-Ups", report_common_power_ups),
    "avg_players_per_match": ("Average Players per Match", report_avg_players_per_match),
    "win_rate_by_side": ("Win Rate by Side", report_win_rate_by_side),
}


def run_report(key):
    """(columns, rows) for the report registered under 'key' in REPORTS."""
    return REPORTS[key][1]()
