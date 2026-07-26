DROP TABLE IF EXISTS game_event         CASCADE;
DROP TABLE IF EXISTS game_participant   CASCADE;
DROP TABLE IF EXISTS friendship         CASCADE;
DROP TABLE IF EXISTS game               CASCADE;
DROP TABLE IF EXISTS game_build         CASCADE;
DROP TABLE IF EXISTS power_up           CASCADE;
DROP TABLE IF EXISTS event_type         CASCADE;
DROP TABLE IF EXISTS player             CASCADE;

DROP TYPE IF EXISTS effect_type;
DROP TYPE IF EXISTS power_up_audience;
DROP TYPE IF EXISTS game_status;
DROP TYPE IF EXISTS game_side;
DROP TYPE IF EXISTS participant_role;
DROP TYPE IF EXISTS friendship_status;


-- ENUM types
CREATE TYPE effect_type         AS ENUM ('reveal_hiders', 'reveal_hunters', 'speed_boost', 'boundary_freeze');
CREATE TYPE power_up_audience   AS ENUM ('hunter', 'hider', 'both');
CREATE TYPE game_status         AS ENUM ('pending', 'active', 'completed', 'cancelled');
CREATE TYPE game_side           AS ENUM ('hunters', 'hiders');
CREATE TYPE participant_role    AS ENUM ('hunter', 'hider');
CREATE TYPE friendship_status   AS ENUM ('pending', 'accepted', 'blocked');


-- PLAYER
CREATE TABLE player (
    player_id     INTEGER       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username      VARCHAR(30)   NOT NULL UNIQUE,
    email         VARCHAR(255)  NOT NULL UNIQUE,
    display_name  VARCHAR(50),
    avatar_url    VARCHAR(2048),
    created_at    TIMESTAMPTZ   NOT NULL DEFAULT now(),
    is_banned     BOOLEAN       NOT NULL DEFAULT false
);


-- EVENT_TYPE
CREATE TABLE event_type (
    event_type_code  VARCHAR(20)  PRIMARY KEY,
    display_name     VARCHAR(64)  NOT NULL,
    description      TEXT
);


-- GAME_BUILD
CREATE TABLE game_build (
    build_id              INTEGER       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name                  VARCHAR(100)  NOT NULL,
    description           TEXT,
    boundary_shrink_rate  NUMERIC(6,2)  NOT NULL,
    initial_radius        INTEGER       NOT NULL,
    final_radius          INTEGER       NOT NULL,
    match_duration        INTEGER       NOT NULL,
    created_at            TIMESTAMPTZ   NOT NULL DEFAULT now(),
    player_id             INTEGER       REFERENCES player(player_id) ON DELETE SET NULL,

    CONSTRAINT chk_radius_order CHECK (final_radius <= initial_radius),
    CONSTRAINT chk_positive_duration CHECK (match_duration > 0)
);


-- POWER_UP
CREATE TABLE power_up (
    power_up_id   INTEGER            GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name          VARCHAR(50)        NOT NULL UNIQUE,
    description   TEXT,
    effect_type   effect_type        NOT NULL,
    duration      INTEGER            NOT NULL,
    cooldown_sec  INTEGER            NOT NULL DEFAULT 0,
    available_to  power_up_audience  NOT NULL DEFAULT 'both'
);


-- GAME
CREATE TABLE game (
    game_id       INTEGER       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    invite_code   VARCHAR(8)    NOT NULL UNIQUE,
    status        game_status   NOT NULL DEFAULT 'pending',
    center_lat    NUMERIC(9,6)  NOT NULL,
    center_lng    NUMERIC(9,6)  NOT NULL,
    started_at    TIMESTAMPTZ,
    ended_at      TIMESTAMPTZ,
    winning_side  game_side,
    player_id     INTEGER       NOT NULL REFERENCES player(player_id),
    build_id      INTEGER       NOT NULL REFERENCES game_build(build_id)
);


-- GAME_PARTICIPANT
CREATE TABLE game_participant (
    game_id     INTEGER           NOT NULL REFERENCES game(game_id)   ON DELETE CASCADE,
    player_id   INTEGER           NOT NULL REFERENCES player(player_id),
    role        participant_role  NOT NULL,
    final_role  participant_role,
    joined_at   TIMESTAMPTZ       NOT NULL DEFAULT now(),
    survived    BOOLEAN,

    PRIMARY KEY (game_id, player_id)
);


-- GAME_EVENT
CREATE TABLE game_event (
    event_id          BIGINT        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    latitude          NUMERIC(9,6),
    longitude         NUMERIC(9,6),
    event_time        TIMESTAMPTZ   NOT NULL DEFAULT now(),
    metadata          JSONB,
    game_id           INTEGER       NOT NULL REFERENCES game(game_id) ON DELETE CASCADE,
    player_id         INTEGER       REFERENCES player(player_id),
    target_player_id  INTEGER       REFERENCES player(player_id),
    power_up_id       INTEGER       REFERENCES power_up(power_up_id),
    event_type_code   VARCHAR(20)   NOT NULL REFERENCES event_type(event_type_code)
);


-- FRIENDSHIP
CREATE TABLE friendship (
    player_id_1  INTEGER            NOT NULL REFERENCES player(player_id) ON DELETE CASCADE,
    player_id_2  INTEGER            NOT NULL REFERENCES player(player_id) ON DELETE CASCADE,
    status       friendship_status  NOT NULL DEFAULT 'pending',
    created_at   TIMESTAMPTZ        NOT NULL DEFAULT now(),

    PRIMARY KEY (player_id_1, player_id_2),
    CONSTRAINT chk_friend_order CHECK (player_id_1 < player_id_2)
);


CREATE INDEX idx_game_host             ON game (player_id);
CREATE INDEX idx_game_build            ON game (build_id);
CREATE INDEX idx_game_build_creator    ON game_build (player_id);
CREATE INDEX idx_participant_player    ON game_participant (player_id);
CREATE INDEX idx_event_game_time       ON game_event (game_id, event_time);
CREATE INDEX idx_event_actor           ON game_event (player_id);
CREATE INDEX idx_event_target          ON game_event (target_player_id);
CREATE INDEX idx_event_power_up        ON game_event (power_up_id);
CREATE INDEX idx_event_type            ON game_event (event_type_code);
CREATE INDEX idx_friendship_player2    ON friendship (player_id_2);


INSERT INTO event_type (event_type_code, display_name, description) VALUES
    ('TAG',             'Tag',              'A hunter tagged a hider, converting them.'),
    ('POWER_UP_USE',    'Power-Up Use',     'A player activated a power-up.'),
    ('BOUNDARY_SHRINK', 'Boundary Shrink',  'The play boundary contracted.'),
    ('PLAYER_JOIN',     'Player Join',      'A player joined the match.'),
    ('GAME_START',      'Game Start',       'The match began.'),
    ('GAME_END',        'Game End',         'The match ended.'),
    ('LOCATION_PING',   'Location Ping',    'A periodic location update from a player.');
