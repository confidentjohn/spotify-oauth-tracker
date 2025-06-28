import os
import requests
from spotipy import Spotify
from utils.db_utils import get_db_connection

def get_access_token_for_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT spotify_refresh_token FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        raise Exception(f"No refresh token found for user {user_id}")
    refresh_token = row[0]
    cur.close()
    conn.close()

    token_response = requests.post(
        "https://accounts.spotify.com/api/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": os.environ["SPOTIFY_CLIENT_ID"],
            "client_secret": os.environ["SPOTIFY_CLIENT_SECRET"],
        }
    )
    token_response.raise_for_status()
    return token_response.json()["access_token"]

def get_spotify_client_for_user(user_id):
    token = get_access_token_for_user(user_id)
    return Spotify(auth=token)

def get_spotify_client():
    token_response = requests.post(
        "https://accounts.spotify.com/api/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": os.environ["SPOTIFY_REFRESH_TOKEN"],
            "client_id": os.environ["SPOTIFY_CLIENT_ID"],
            "client_secret": os.environ["SPOTIFY_CLIENT_SECRET"],
        }
    )
    token_response.raise_for_status()
    return Spotify(auth=token_response.json()["access_token"])