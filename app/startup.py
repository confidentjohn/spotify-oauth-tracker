from app.db.init_db import run_init_db
from utils.create_exclusions_playlist import ensure_exclusions_playlist
from utils.spotify_auth import get_spotify_client_for_user

def run_startup_tasks():
    run_init_db()
    from utils.db_utils import get_db_connection

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE spotify_refresh_token IS NOT NULL")
    user_ids = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()

    for user_id in user_ids:
        try:
            sp = get_spotify_client_for_user(user_id)
            ensure_exclusions_playlist(sp, user_id)
        except Exception as e:
            print(f"⚠️ Failed to init Spotify client for user {user_id} (ignored): {e}")

run_startup_tasks()