# Spotify Library & Play History Tracker

## 1. Project Summary

This project is a comprehensive Spotify library and play history tracker built with Python, PostgreSQL, and Flask. It automatically syncs your Spotify saved albums, liked tracks, and play history, and generates smart playlists based on various listening patterns. The backend sync jobs run via GitHub Actions and the Flask frontend provides a UI for manual sync triggers, logs, and token management. The project is designed to be deployed easily on Render.com.

---

## 2. Features

- **Daily Sync** of saved albums and liked tracks
- **Frequent Sync** (every 10 minutes) of recently played tracks
- **Smart Playlists** generated automatically (never played, most played, recently added, etc.)
- **Track Availability Checks** to ensure songs are still available on Spotify
- **Rate Limit Handling** with automatic retries and exponential backoff
- **Flask Web UI** to trigger syncs, view logs, and manage OAuth tokens
- **GitHub Actions** workflows for automation and scheduling
- **Materialized Views** and unified track data for efficient querying and reporting

---

## 3. Folder Structure

```
spotify-oauth-tracker/
├── app/                      # Flask frontend (OAuth, UI, sync triggers)
│   └── app.py
├── api_syncs/                # Spotify sync jobs and track availability checks
│   ├── __init__.py
│   ├── check_track_availability.py  # Checks if tracks are still available on Spotify
│   ├── materialized_views.py         # Creates and refreshes materialized views in DB
│   ├── sync_album_tracks.py          # Syncs tracks for saved albums missing track data
│   ├── sync_liked_tracks_full.py     # Full sync of liked tracks (historical)
│   ├── sync_liked_tracks.py          # Incremental sync of liked tracks
│   ├── sync_saved_albums.py          # Syncs user's saved albums
│   └── track_plays.py                # Syncs recently played tracks every 10 minutes
├── playlists/                # Smart playlist update scripts
│   ├── update_playlist_loved_added_last_30_days.py  # Liked tracks added recently
│   ├── update_playlist_most_played.py                # Tracks with highest play counts
│   ├── update_playlist_never_played.py               # Tracks never played
│   ├── update_playlist_never_played_new_tracks.py   # Newly added tracks never played
│   ├── update_playlist_oldest_played.py              # Tracks played multiple times, oldest first
│   └── update_playlist_played_once.py                 # Tracks played exactly once
├── db/                       # Database initialization script
│   └── init_db.py
├── reports/                  # Usage reports and analytics (not detailed here)
├── utils/                    # Shared utilities for logging and DB access
├── .github/workflows/        # GitHub Actions workflows for automation
│   ├── build_unified_tracks.yml
│   ├── check_track_availability.yml
│   ├── master_sync.yml
│   ├── sync_album_tracks.yml
│   ├── sync_albums.yml
│   ├── sync_liked_tracks_full.yml
│   ├── sync_liked_tracks.yml
│   ├── track_plays.yml
│   └── update_all_playlists.yml
├── render.yaml               # Render deployment configuration
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

---

## 4. Database Schema

| Table                | Purpose                                                  |
|----------------------|----------------------------------------------------------|
| `albums`             | Stores user's saved albums                                |
| `liked_tracks`       | All liked tracks with metadata                            |
| `tracks`             | Tracks from albums, includes metadata                     |
| `plays`              | Complete history of played tracks                         |
| `playlist_mappings`  | Maps playlist slugs to Spotify playlist IDs              |
| `track_availability` | Stores availability status and last checked timestamp    |
| `logs`               | Logs output from sync scripts for debugging              |
| `unified_tracks`     | Materialized view consolidating tracks, plays, and likes |
| `materialized_views` | Managed via script for optimized querying                 |

Tracks may be orphaned (not liked or in albums) and are cleaned automatically.

---

## 5. Smart Playlist Descriptions

| Script                                    | Playlist Logic                                         |
|-------------------------------------------|-------------------------------------------------------|
| `update_playlist_never_played.py`         | Tracks that have never been played                     |
| `update_playlist_played_once.py`          | Tracks played exactly once                             |
| `update_playlist_oldest_played.py`        | Tracks played multiple times, oldest first             |
| `update_playlist_most_played.py`          | Tracks with the highest play counts                     |
| `update_playlist_loved_added_last_30_days.py` | Liked tracks added within the last 30 days           |
| `update_playlist_never_played_new_tracks.py`  | Newly added tracks that have never been played        |

---

## 6. GitHub Actions Workflows and Triggers

| Workflow File                  | Trigger / Schedule           | Purpose                                  |
|-------------------------------|-----------------------------|------------------------------------------|
| `check_track_availability.yml`| Manual / Reusable            | Checks if tracks are still available     |
| `master_sync.yml`              | Daily at 07:07 UTC           | Runs full sync of albums, tracks, likes  |
| `sync_album_tracks.yml`        | Reusable                    | Syncs album track details                  |
| `sync_albums.yml`              | Reusable                    | Syncs saved albums                         |
| `sync_liked_tracks.yml`        | Reusable                    | Syncs liked tracks incrementally           |
| `sync_liked_tracks_full.yml`   | Reusable                    | Full liked tracks sync                      |
| `track_plays.yml`              | Every 10 minutes             | Syncs recent play history                   |
| `update_all_playlists.yml`     | Daily at 10:00 UTC           | Regenerates all smart playlists             |
| `build_unified_tracks.yml`     | Manual / Scheduled           | Builds and refreshes materialized views    |

---

## 7. Environment Variables

| Variable Name           | Description                          |
|------------------------|------------------------------------|
| `SPOTIFY_CLIENT_ID`     | Spotify Developer App Client ID     |
| `SPOTIFY_CLIENT_SECRET` | Spotify Developer App Client Secret |
| `SPOTIFY_REFRESH_TOKEN` | Refresh token for Spotify OAuth     |
| `SPOTIFY_REDIRECT_URI`  | OAuth Redirect URI                  |
| `DB_HOST`               | PostgreSQL database host            |
| `DB_PORT`               | PostgreSQL database port            |
| `DB_NAME`               | PostgreSQL database name            |
| `DB_USER`               | PostgreSQL username                 |
| `DB_PASSWORD`           | PostgreSQL password                 |
| `FLASK_SECRET`          | Flask app secret key for sessions   |

---

## 8. Setup Instructions

### Clone the Repository

```bash
git clone https://github.com/confidentjohn/spotify-oauth-tracker.git
cd spotify-oauth-tracker
```

### Register a Spotify Developer App

- Create an app at the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/applications)
- Set Redirect URI to `https://<your-app>.onrender.com/callback`

### Deploy to Render.com

- Add a new Web Service pointing to `app/app.py`
- Set all required environment variables listed above
- Enable auto-deploy from GitHub

### Obtain Refresh Token

- Visit `/login` on your deployed site
- Authenticate with Spotify
- Copy the refresh token from the `/callback` response

### Initialize the Database

- Visit `/init-db` endpoint to create necessary tables and constraints

### Add Playlist Mappings

Insert playlist mappings into the database, e.g.:

```sql
INSERT INTO playlist_mappings (slug, name, playlist_id)
VALUES ('never_played', 'Never Played', 'your_spotify_playlist_id');
```

Repeat for each smart playlist.

---

## 9. Sync Triggers via Flask UI

You can manually trigger syncs or playlist updates via these endpoints:

- `/sync-saved-albums` — Sync saved albums
- `/sync-album-tracks` — Sync tracks for albums missing data
- `/sync-liked-tracks` — Sync liked tracks incrementally
- `/sync-liked-tracks-full` — Full liked tracks sync
- `/run-tracker` — Run all syncs sequentially
- `/update-never-played-playlist` — Update the "Never Played" playlist
- `/update-most-played-playlist` — Update the "Most Played" playlist
- `/update-played-once-playlist` — Update the "Played Once" playlist
- `/update-oldest-played-playlist` — Update the "Oldest Played" playlist
- `/update-loved-added-last-30-days-playlist` — Update recently loved playlist
- `/update-never-played-new-tracks-playlist` — Update newly added never played playlist

---

## 10. Architecture Diagram

```mermaid
graph TD
    subgraph GitHub_Actions
        A[track_plays.py]
        B[sync_saved_albums.py]
        C[sync_album_tracks.py]
        D[sync_liked_tracks.py]
        E[check_track_availability.py]
        F[update_all_playlists.py]
        G[build_unified_tracks.py]
    end

    subgraph Flask_Web_UI
        H[app.py]
    end

    subgraph PostgreSQL_DB
        DB[(Database)]
        MV[Materialized Views]
    end

    A --> DB
    B --> DB
    C --> DB
    D --> DB
    E --> DB
    F --> DB
    G --> MV
    MV --> DB
    H --> DB
    H --> Spotify[(Spotify API)]
    F --> Spotify
    E --> Spotify
```

---

## 11. Rate Limit Handling

All Spotify API requests are wrapped with logic to:

- Detect `429 Too Many Requests` responses
- Wait for the specified `Retry-After` duration
- Retry with exponential backoff if needed

This ensures smooth syncing without manual intervention despite Spotify rate limits.

---

## 12. Testing Instructions

- Run individual sync scripts locally, e.g.:

  ```bash
  python api_syncs/sync_liked_tracks.py
  ```

- Use Flask routes to test UI-triggered syncs and observe logs, e.g.:

  - `/sync-saved-albums`
  - `/sync-album-tracks`
  - `/sync-liked-tracks`

- Inspect the `logs` table for detailed output and errors
- Verify materialized views and `unified_tracks` table for correct data aggregation
- Test track availability updates by running `check_track_availability.py`
- Simulate rate limiting by mocking `429` responses and confirm retry behavior

---

## 13. Maintenance Notes

- `init_db.py` creates tables and enforces constraints
- `sync_album_tracks.py` only syncs albums missing track details
- `track_plays.py` runs every 10 minutes and logs play history
- Orphan tracks (not liked and not in albums) are cleaned automatically
- Play history (`plays` table) is never deleted, even if tracks are removed from library
- Materialized views are refreshed regularly to optimize queries
- Playlist update scripts rely on `playlist_mappings` for Spotify playlist IDs

---

Feel free to fork, contribute, and extend this project to fit your Spotify tracking needs!
