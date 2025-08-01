import os
import psycopg2
import requests
import fcntl
import time
from datetime import datetime, timedelta
from spotipy import Spotify
from spotipy.exceptions import SpotifyException
from utils.logger import log_event
from dateutil import parser
from utils.spotify_auth import get_spotify_client

LOCK_FILE = "/tmp/sync_library.lock"

def safe_spotify_call(func, *args, **kwargs):
    retries = 0
    while True:
        try:
            return func(*args, **kwargs)
        except SpotifyException as e:
            if e.http_status == 429:
                retry_after = int(e.headers.get("Retry-After", 5))
                retries += 1
                log_event("sync_liked_tracks", f"Rate limit hit. Retry #{retries} in {retry_after}s")
                time.sleep(retry_after)
            else:
                log_event("sync_liked_tracks", f"Spotify error: {e}", level="error")
                raise

# Acquire lock to avoid overlap
with open(LOCK_FILE, 'w') as lock_file:
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log_event("sync_liked_tracks", "Another sync is already running", level="warning")
        exit(1)

    sp = get_spotify_client()

    from utils.db_utils import get_db_connection
    conn = get_db_connection()
    cur = conn.cursor()

    now = datetime.now(tz=None).astimezone()  # keep UTC-awareness
    FRESH_LIKED_CUTOFF_DAYS = int(os.environ.get("FRESH_LIKED_CUTOFF_DAYS", "30"))
    fresh_cutoff = now - timedelta(days=FRESH_LIKED_CUTOFF_DAYS)

    limit = 50
    offset = 0
    batch_size = 50
    counter = 0
    liked_track_ids = set()
    skipped_due_to_freshness = 0
    updated_liked_tracks = 0

    stop_fetching = False

    log_event("sync_liked_tracks", "Starting liked tracks sync")

    while True:
        results = safe_spotify_call(sp.current_user_saved_tracks, limit=limit, offset=offset)
        items = results['items']
        log_event("sync_liked_tracks", f"Processing batch: offset={offset}, size={len(items)}")

        if not items:
            break

        if items and parser.isoparse(items[-1]['added_at']) < fresh_cutoff:
            stop_fetching = True

        for item in items:
            track = item['track']
            if not track:
                continue

            track_id = track['id']
            liked_added_at = parser.isoparse(item['added_at'])
            if liked_added_at.tzinfo is None:
                from datetime import timezone
                liked_added_at = liked_added_at.replace(tzinfo=timezone.utc)
            # Only skip tracks older than fresh_cutoff
            if liked_added_at < fresh_cutoff:
                continue
            liked_track_ids.add(track_id)

            track_name = track['name']
            track_artist = track['artists'][0]['name']
            artist_id = track['artists'][0]['id']
            artist = track['artists'][0]['name']
            album = track['album']['name']
            album_id = track['album']['id']

            duration_ms = track.get('duration_ms')
            popularity = track.get('popularity')

            cur.execute("SELECT added_at FROM albums WHERE id = %s", (album_id,))
            album_row = cur.fetchone()
            album_added_at = album_row[0] if album_row else None
            final_added_at = album_added_at if album_added_at else liked_added_at

            # Removed insertion into tracks table as per instructions

            # Check if album is in library
            cur.execute("SELECT 1 FROM albums WHERE id = %s", (album_id,))
            album_in_library = cur.fetchone() is not None

            # Insert into liked_tracks table
            cur.execute("""
                INSERT INTO liked_tracks (
                    track_id, liked_at, added_at, last_checked_at,
                    track_name, track_artist, artist_id, album_id, album_in_library, duration_ms, popularity
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (track_id) DO UPDATE 
                SET liked_at = EXCLUDED.liked_at,
                    added_at = EXCLUDED.added_at,
                    last_checked_at = EXCLUDED.last_checked_at,
                    track_name = EXCLUDED.track_name,
                    track_artist = EXCLUDED.track_artist,
                    artist_id = EXCLUDED.artist_id,
                    album_id = EXCLUDED.album_id,
                    album_in_library = EXCLUDED.album_in_library,
                    duration_ms = EXCLUDED.duration_ms,
                    popularity = EXCLUDED.popularity;
            """, (track_id, liked_added_at, final_added_at, now, track_name, track_artist, artist_id, album_id, album_in_library, duration_ms, popularity))

            updated_liked_tracks += 1
            counter += 1
            if counter % 500 == 0:
                log_event("sync_liked_tracks", f"Updated {counter} tracks so far")
            if counter % batch_size == 0:
                conn.commit()

        if stop_fetching:
            break

        offset += len(items)
        if len(items) < limit:
            break

    if stop_fetching:
        log_event("sync_liked_tracks", "Stopping fetch early: reached tracks older than fresh_cutoff")

    log_event("sync_liked_tracks", f"{len(liked_track_ids)} liked tracks synced")
    log_event("sync_liked_tracks", f"Finished scanning liked tracks. Total fetched: {counter}")

    conn.commit()
    log_event("sync_liked_tracks", f"✅ {updated_liked_tracks} tracks updated")
    log_event("sync_liked_tracks", f"⏭️ {skipped_due_to_freshness} tracks skipped due to recent check")
    cur.close()
    conn.close()
    log_event("sync_liked_tracks", "Liked tracks sync complete")