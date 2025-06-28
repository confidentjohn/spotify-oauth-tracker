import os
import sys
import time
import requests
import psycopg2
from spotipy import Spotify
from spotipy.exceptions import SpotifyException
from datetime import datetime

# ─────────────────────────────────────────────
# Ensure utils is in path
# ─────────────────────────────────────────────
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.logger import log_event

# ─────────────────────────────────────────────
# Safe Spotify API Wrapper
# ─────────────────────────────────────────────
def safe_spotify_call(func, *args, **kwargs):
    retries = 0
    while True:
        try:
            return func(*args, **kwargs)
        except SpotifyException as e:
            if e.http_status == 429:
                retry_after = int(e.headers.get("Retry-After", 5))
                retries += 1
                log_event("track_plays", f"Rate limit hit. Retry #{retries} in {retry_after}s")
                time.sleep(retry_after)
            else:
                log_event("track_plays", f"Spotify error: {e}", level="error")
                raise
        except requests.exceptions.ReadTimeout as e:
            retries += 1
            log_event("track_plays", f"Timeout hit. Retry #{retries} in 5s... ({e})")
            time.sleep(5)

# ─────────────────────────────────────────────
# Setup Spotify client
# ─────────────────────────────────────────────
from utils.spotify_auth import get_spotify_client_for_user

from utils.db_utils import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

cur.execute("SELECT id FROM users WHERE spotify_refresh_token IS NOT NULL")
user_ids = [row[0] for row in cur.fetchall()]

if not user_ids:
    log_event("track_plays", "❌ No users found in database", level="error")
    sys.exit(1)

for user_id in user_ids:
    try:
        sp = get_spotify_client_for_user(user_id)

        log_event("track_plays", f"Tracking recently played tracks for user {user_id}")
        results = safe_spotify_call(sp.current_user_recently_played, limit=50)
        recent_plays = results["items"]

        new_count = 0
        for item in recent_plays:
            track = item["track"]
            track_id = track["id"]
            played_at = item["played_at"]
            from dateutil import parser
            played_at_dt = parser.isoparse(played_at)

            cur.execute("SELECT 1 FROM plays WHERE track_id = %s AND played_at = %s AND user_id = %s", (track_id, played_at_dt, user_id))
            if cur.fetchone():
                continue

            cur.execute("""
                INSERT INTO plays (track_id, played_at, user_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (track_id, played_at, user_id) DO NOTHING;
            """, (track_id, played_at_dt, user_id))
            new_count += 1
            time.sleep(0.1)  # optional light throttle

        log_event("track_plays", f"✅ User {user_id}: Tracked {new_count} new play(s).")
    except Exception as e:
        log_event("track_plays", f"❌ User {user_id} failed: {e}", level="error")

conn.commit()
cur.close()
conn.close()
