# Manhunt Game Database Platform

A PostgreSQL-supported database and two PySide6 desktop apps for a
enhanced version of the backyard game Manhunt (CS 5614 project).

This README.md walks through the setup and usage of the app.

## 1. Install dependencies

```bash
pip install -r requirements.txt
```

## 2. Create the schema

Create a PostgreSQL database and run the command:
```bash
psql -d manhunt -f manhunt_schema.sql
```

Open `db.py` and edit `CONFIG` dict to point at the built database.

```python
CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "manhunt",
    "user": "your_username",
    "password": "your_password",
}
```

## 3. Seed demo data

```bash
python seed_data.py
```

Populates 75 players, friendships, a handful of game builds and
power-ups, 40 games, participants, and simulated event logs.

## 4. Run the apps

The player and admin apps are two independent guis.

```bash
python player_gui.py
python admin_gui.py
```

## How it's organized

- **`manhunt_schema.sql`** — the database schema (tables, enums, indexes, `event_type` seed rows).
- **`db.py`** — the only module that opens database connections; generic query/command helpers plus lookups shared by both apps (e.g. fetching a player, listing game builds).
- **`player_app.py`** — backend functions for player use cases: account, friends, hosting/joining games, match history.
- **`admin_app.py`** — backend functions for admin use cases: search/filter, player management (ban/unban), leaderboard reports.
- **`player_gui.py`** — the player-facing PySide6 GUI (Account, Friends, Transfer, History tabs), gated behind a login/register dialog.
- **`admin_gui.py`** — the admin-facing PySide6 GUI (Query & Search, Manage Players, Leaderboard tabs).
- **`seed_data.py`** — one-shot Faker-based demo data generator.

Every tab in both GUIs follows the same layout: controls on the left,
a table of relevant data on the right. Creating and editing game builds
is not yet implemented in either GUI — builds are only selected from a
dropdown when hosting a game.
