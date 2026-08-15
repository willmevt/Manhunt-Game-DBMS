import random
import string

import psycopg2

import db


# ==================== Account ====================

def login(username):
    """Look up a player by username for the login dialog. Returns a player row or None."""
    return db.get_player_by_username(username)


def create_account(username, email, display_name=None, avatar_url=None):
    """Insert a new player row. Returns the new player_id. Raises on duplicate username/email."""
    row = db.run_command_returning(
        """
        INSERT INTO player (username, email, display_name, avatar_url)
        VALUES (%s, %s, %s, %s)
        RETURNING player_id;
        """,
        (username, email, display_name, avatar_url),
    )
    return row[0]


def get_account(player_id):
    """Return the current player's row, or None."""
    return db.get_player_by_id(player_id)


def update_account(player_id, display_name=None, avatar_url=None):
    """Update the mutable profile fields (username/email are immutable post-registration)."""
    return db.run_command(
        """
        UPDATE player
        SET display_name = %s, avatar_url = %s
        WHERE player_id = %s;
        """,
        (display_name, avatar_url, player_id),
    )


def list_all_players_brief():
    """(columns, rows) of all players — feeds the Account tab's right-side demo table."""
    return db.run_query(
        """
        SELECT player_id, username, email, display_name, avatar_url, created_at, is_banned
        FROM player
        ORDER BY player_id;
        """
    )


# ==================== Friends ====================

def _ordered_pair(a, b):
    """friendship's PK/check constraint requires player_id_1 < player_id_2."""
    return (a, b) if a < b else (b, a)


def send_friend_request(from_player_id, to_username):
    """Send a friend request by target username. Raises ValueError on bad input or a pre-existing row."""
    target = db.get_player_by_username(to_username)
    if target is None:
        raise ValueError(f"No player named '{to_username}'.")
    to_player_id = target[0]
    if to_player_id == from_player_id:
        raise ValueError("You cannot send a friend request to yourself.")

    p1, p2 = _ordered_pair(from_player_id, to_player_id)
    rowcount = db.run_command(
        """
        INSERT INTO friendship (player_id_1, player_id_2, status)
        VALUES (%s, %s, 'pending')
        ON CONFLICT (player_id_1, player_id_2) DO NOTHING;
        """,
        (p1, p2),
    )
    if rowcount == 0:
        raise ValueError("A friendship (or pending request) already exists with that player.")


def respond_friend_request(player_id_1, player_id_2, accept):
    """Accept (status -> accepted) or reject (delete) a pending friend request."""
    p1, p2 = _ordered_pair(player_id_1, player_id_2)
    if accept:
        return db.run_command(
            """
            UPDATE friendship
            SET status = 'accepted'
            WHERE player_id_1 = %s AND player_id_2 = %s AND status = 'pending';
            """,
            (p1, p2),
        )
    return db.run_command(
        """
        DELETE FROM friendship
        WHERE player_id_1 = %s AND player_id_2 = %s AND status = 'pending';
        """,
        (p1, p2),
    )


def remove_friend(player_id_a, player_id_b):
    """Remove an existing accepted friendship."""
    p1, p2 = _ordered_pair(player_id_a, player_id_b)
    return db.run_command(
        """
        DELETE FROM friendship
        WHERE player_id_1 = %s AND player_id_2 = %s AND status = 'accepted';
        """,
        (p1, p2),
    )


def list_friends(player_id):
    """(columns, rows) of the current player's accepted friends."""
    return db.run_query(
        """
        SELECT p.player_id, p.username, p.display_name, f.created_at AS friends_since
        FROM friendship f
        JOIN player p ON p.player_id = CASE
            WHEN f.player_id_1 = %s THEN f.player_id_2
            ELSE f.player_id_1
        END
        WHERE (f.player_id_1 = %s OR f.player_id_2 = %s) AND f.status = 'accepted'
        ORDER BY p.username;
        """,
        (player_id, player_id, player_id),
    )


def list_pending_friend_requests(player_id):
    """
    (columns, rows) of all pending friendship rows involving the current player.
    Note: the schema has no "requested_by" column, so incoming vs outgoing
    requests can't be distinguished — both parties can Accept or Reject.
    """
    return db.run_query(
        """
        SELECT f.player_id_1, f.player_id_2, p1.username AS username_1,
               p2.username AS username_2, f.created_at
        FROM friendship f
        JOIN player p1 ON p1.player_id = f.player_id_1
        JOIN player p2 ON p2.player_id = f.player_id_2
        WHERE (f.player_id_1 = %s OR f.player_id_2 = %s) AND f.status = 'pending'
        ORDER BY f.created_at;
        """,
        (player_id, player_id),
    )


# ==================== Transfer (host / join game) ====================

VALID_ROLES = ("hunter", "hider")


def _generate_invite_code():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def host_game(player_id, build_id, center_lat, center_lng, initial_role):
    """
    Create a new pending game hosted by player_id, and add the host as its
    first participant. Both inserts happen in one transaction. Returns
    (game_id, invite_code).
    """
    if initial_role not in VALID_ROLES:
        raise ValueError(f"Role must be one of {VALID_ROLES}.")

    attempts = 5
    last_error = None
    for _ in range(attempts):
        invite_code = _generate_invite_code()
        try:
            with db.get_cursor(commit=True) as cur:
                cur.execute(
                    """
                    INSERT INTO game (invite_code, center_lat, center_lng, player_id, build_id)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING game_id;
                    """,
                    (invite_code, center_lat, center_lng, player_id, build_id),
                )
                game_id = cur.fetchone()[0]
                cur.execute(
                    """
                    INSERT INTO game_participant (game_id, player_id, role)
                    VALUES (%s, %s, %s);
                    """,
                    (game_id, player_id, initial_role),
                )
                return game_id, invite_code
        except psycopg2.errors.UniqueViolation as e:
            last_error = e
            continue
    raise RuntimeError("Could not generate a unique invite code, please try again.") from last_error


def join_game(player_id, invite_code, role):
    """
    Join a pending game by invite code. Returns the game_id. Raises
    ValueError if the code is unknown, the game is no longer open, or the
    player has already joined.
    """
    if role not in VALID_ROLES:
        raise ValueError(f"Role must be one of {VALID_ROLES}.")

    with db.get_cursor(commit=True) as cur:
        cur.execute(
            "SELECT game_id, status FROM game WHERE invite_code = %s FOR UPDATE;",
            (invite_code,),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError("Invite code not found.")
        game_id, status = row
        if status != "pending":
            raise ValueError("This game is no longer open to join.")

        try:
            cur.execute(
                """
                INSERT INTO game_participant (game_id, player_id, role)
                VALUES (%s, %s, %s);
                """,
                (game_id, player_id, role),
            )
        except psycopg2.errors.UniqueViolation:
            raise ValueError("You have already joined this game.")
        return game_id


def list_open_games():
    """(columns, rows) of pending games available to join — feeds the Transfer tab's right-side table."""
    return db.run_query(
        """
        SELECT g.game_id, g.invite_code, gb.name AS build_name, g.center_lat, g.center_lng,
               host.username AS host_username,
               (SELECT COUNT(*) FROM game_participant gp WHERE gp.game_id = g.game_id) AS participant_count
        FROM game g
        JOIN game_build gb ON gb.build_id = g.build_id
        JOIN player host ON host.player_id = g.player_id
        WHERE g.status = 'pending'
        ORDER BY g.game_id DESC;
        """
    )


# ==================== Live Game Activity ====================

def list_my_active_games(player_id):
    """(columns, rows) of games the player is currently part of (pending/active)."""
    return db.run_query(
        """
        SELECT g.game_id, g.invite_code, g.status, gp.role,
               g.center_lat, g.center_lng, gb.initial_radius, gb.name AS build_name
        FROM game_participant gp
        JOIN game g ON g.game_id = gp.game_id
        JOIN game_build gb ON gb.build_id = g.build_id
        WHERE gp.player_id = %s AND g.status IN ('pending', 'active')
        ORDER BY g.game_id DESC;
        """,
        (player_id,),
    )


def list_other_participants(game_id, player_id):
    """(columns, rows) of the other players in a game — feeds the "tag target" dropdown."""
    return db.run_query(
        """
        SELECT p.player_id, p.username
        FROM game_participant gp
        JOIN player p ON p.player_id = gp.player_id
        WHERE gp.game_id = %s AND gp.player_id != %s
        ORDER BY p.username;
        """,
        (game_id, player_id),
    )


def list_power_ups_for_role(role):
    """(columns, rows) of power-ups usable by the given participant_role."""
    return db.run_query(
        """
        SELECT power_up_id, name, effect_type, duration, cooldown_sec
        FROM power_up
        WHERE available_to = %s OR available_to = 'both'
        ORDER BY name;
        """,
        (role,),
    )


def _jitter_point(center_lat, center_lng, radius_m):
    """A random point within radius_m meters of the given center (same formula as seed_data.py)."""
    lat = center_lat + random.uniform(-radius_m, radius_m) / 111_000
    lng = center_lng + random.uniform(-radius_m, radius_m) / 111_000
    return round(lat, 6), round(lng, 6)


def log_location_ping(game_id, player_id, center_lat, center_lng, radius_m):
    """Insert a LOCATION_PING event near the game's center."""
    lat, lng = _jitter_point(float(center_lat), float(center_lng), radius_m)
    db.run_command(
        """
        INSERT INTO game_event (latitude, longitude, game_id, player_id, event_type_code)
        VALUES (%s, %s, %s, %s, 'LOCATION_PING');
        """,
        (lat, lng, game_id, player_id),
    )


def log_tag(game_id, tagger_id, target_id, center_lat, center_lng, radius_m):
    """Insert a TAG event. Logging only — does not mutate game_participant/game state."""
    if tagger_id == target_id:
        raise ValueError("You cannot tag yourself.")
    lat, lng = _jitter_point(float(center_lat), float(center_lng), radius_m)
    db.run_command(
        """
        INSERT INTO game_event (latitude, longitude, game_id, player_id, target_player_id, event_type_code)
        VALUES (%s, %s, %s, %s, %s, 'TAG');
        """,
        (lat, lng, game_id, tagger_id, target_id),
    )


def log_power_up_use(game_id, player_id, power_up_id):
    """Insert a POWER_UP_USE event (no lat/lng, matching seed_data.py's convention)."""
    db.run_command(
        """
        INSERT INTO game_event (game_id, player_id, power_up_id, event_type_code)
        VALUES (%s, %s, %s, 'POWER_UP_USE');
        """,
        (game_id, player_id, power_up_id),
    )


def list_recent_game_events(game_id, limit=30):
    """(columns, rows) of the most recent events for a game — feeds the live event feed table."""
    return db.run_query(
        """
        SELECT ge.event_id, ge.event_type_code, actor.username AS player,
               target.username AS target_player, ge.latitude, ge.longitude,
               ge.event_time, pu.name AS power_up
        FROM game_event ge
        LEFT JOIN player actor ON actor.player_id = ge.player_id
        LEFT JOIN player target ON target.player_id = ge.target_player_id
        LEFT JOIN power_up pu ON pu.power_up_id = ge.power_up_id
        WHERE ge.game_id = %s
        ORDER BY ge.event_time DESC
        LIMIT %s;
        """,
        (game_id, limit),
    )


# ==================== History ====================

def get_player_history(player_id):
    """(columns, rows) of the current player's past/ongoing matches."""
    return db.run_query(
        """
        SELECT gp.game_id, g.invite_code, gp.role, gp.final_role, gp.survived,
               g.status, g.started_at, g.ended_at, g.winning_side
        FROM game_participant gp
        JOIN game g ON g.game_id = gp.game_id
        WHERE gp.player_id = %s
        ORDER BY g.started_at DESC NULLS LAST, gp.game_id DESC;
        """,
        (player_id,),
    )


def get_player_stats(player_id):
    """
    Return {"total_games": int, "wins": int, "total_tags_landed": int}.
    participant_role ('hunter'/'hider') and game_side ('hunters'/'hiders')
    use different spellings, so wins are computed via an explicit mapping.
    """
    _, rows = db.run_query(
        """
        SELECT
            (SELECT COUNT(*) FROM game_participant WHERE player_id = %s) AS total_games,
            (SELECT COUNT(*)
             FROM game_participant gp
             JOIN game g ON g.game_id = gp.game_id
             WHERE gp.player_id = %s
               AND g.status = 'completed'
               AND g.winning_side = (CASE gp.final_role
                                          WHEN 'hunter' THEN 'hunters'
                                          WHEN 'hider' THEN 'hiders'
                                      END)::game_side
            ) AS wins,
            (SELECT COUNT(*) FROM game_event WHERE player_id = %s AND event_type_code = 'TAG') AS total_tags_landed;
        """,
        (player_id, player_id, player_id),
    )
    total_games, wins, total_tags_landed = rows[0]
    return {
        "total_games": total_games,
        "wins": wins,
        "total_tags_landed": total_tags_landed,
    }
