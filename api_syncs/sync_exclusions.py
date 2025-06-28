import os
import psycopg2
from spotipy.exceptions import SpotifyException
from utils.logger import log_event
from utils.spotify_auth import get_spotify_client_for_user
from utils.db_utils import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

cur.execute("SELECT id FROM users WHERE spotify_refresh_token IS NOT NULL")
user_ids = [row[0] for row in cur.fetchall()]

for user_id in user_ids:
    try:
        sp = get_spotify_client_for_user(user_id)

        cur.execute("SELECT playlist_id FROM playlist_mappings WHERE name = %s AND user_id = %s", ("exclusions", user_id))
        row = cur.fetchone()
        if not row:
            log_event("sync_exclusions", f"❌ No 'exclusions' playlist for user {user_id}.")
            continue

        playlist_url = row[0]
        playlist_id = playlist_url.split("/")[-1].split("?")[0]
        log_event("sync_exclusions", f"🎯 User {user_id}: Using playlist ID: {playlist_id}")

        # Fetch track IDs from the playlist
        track_ids = []
        offset = 0
        while True:
            results = sp.playlist_items(playlist_id, offset=offset, fields="items.track.id,total,next", additional_types=["track"])
            items = results.get("items", [])
            if not items:
                break
            for item in items:
                track = item.get("track")
                if track and track.get("id"):
                    track_ids.append(track["id"])
            offset += len(items)

        log_event("sync_exclusions", f"📦 User {user_id}: Retrieved {len(track_ids)} track(s) to exclude.")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS excluded_tracks (
                track_id TEXT,
                user_id INTEGER,
                PRIMARY KEY (track_id, user_id)
            )
        """)
        cur.execute("DELETE FROM excluded_tracks WHERE user_id = %s", (user_id,))
        for track_id in track_ids:
            cur.execute("INSERT INTO excluded_tracks (track_id, user_id) VALUES (%s, %s)", (track_id, user_id))

        conn.commit()
        log_event("sync_exclusions", f"✅ User {user_id}: excluded_tracks table updated.")
    except Exception as e:
        log_event("sync_exclusions", f"❌ User {user_id} failed: {e}", level="error")

cur.close()
conn.close()