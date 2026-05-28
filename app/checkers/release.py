"""
app/checkers/release.py
-----------------------
Checker for movie and TV show release alerts.

Uses the TMDB (The Movie Database) API to check whether a title has been released.
TMDB was chosen because:
  - Free with a simple registration
  - Comprehensive database of movies and TV shows worldwide
  - Well-documented REST API with good search capabilities

API docs: https://developer.themoviedb.org/docs

How it works:
  1. Extract season number from the query if present ("Severance temporada 3" → 3)
  2. Clean the query to remove season indicators before searching TMDB
  3. Search TMDB for the title
  4. If a season was specified, fetch that season's air date specifically
  5. Compare the release date to today
"""

import httpx
import re
from datetime import datetime, timezone
from app.core.config import settings

BASE_URL = "https://api.themoviedb.org/3"


def extract_season_number(query: str) -> int | None:
    """
    Extracts a season number from the query string if one is present.

    Supports multiple formats: "temporada 3", "season 3", "t3", "s3"

    Args:
        query: the user's search string e.g. "Severance temporada 3"

    Returns:
        The season number as an integer, or None if not found
    """
    patterns = [
        r"temporada\s+(\d+)",   # Spanish: "temporada 3"
        r"season\s+(\d+)",      # English: "season 3"
        r"\bt(\d+)\b",          # Short form: "t3"
        r"\bs(\d+)\b",          # Short form: "s3"
    ]
    for pattern in patterns:
        match = re.search(pattern, query.lower())
        if match:
            return int(match.group(1))
    return None


def clean_query(query: str) -> str:
    """
    Removes season indicators from the query before sending it to TMDB.

    TMDB's search doesn't understand "temporada 3" — searching for
    "Severance temporada 3" returns no results. We need to search for
    just "Severance" and then look up the season separately.

    Args:
        query: the original user query e.g. "Severance temporada 3"

    Returns:
        The cleaned query e.g. "Severance"
    """
    patterns = [
        r"temporada\s+\d+",
        r"season\s+\d+",
        r"\bt\d+\b",
        r"\bs\d+\b",
    ]
    clean = query
    for pattern in patterns:
        clean = re.sub(pattern, "", clean, flags=re.IGNORECASE)
    return clean.strip()


def search_tmdb(query: str, media_type: str) -> dict | None:
    """
    Searches TMDB for a movie or TV show and returns the top result.

    Args:
        query: cleaned search string e.g. "Severance"
        media_type: "movie" or "tv"

    Returns:
        The first result as a dict, or None if nothing found
    """
    response = httpx.get(
        f"{BASE_URL}/search/{media_type}",
        params={"query": query, "language": "es-ES", "api_key": settings.tmdb_api_key},
        timeout=10,
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    return results[0] if results else None


def get_season_air_date(tmdb_id: int, season_number: int) -> str | None:
    """
    Fetches the air date of a specific season of a TV show.

    Args:
        tmdb_id: the TMDB internal ID of the show
        season_number: the season to look up e.g. 3

    Returns:
        The air date as a string "YYYY-MM-DD", or None if not found/announced
    """
    response = httpx.get(
        f"{BASE_URL}/tv/{tmdb_id}/season/{season_number}",
        params={"api_key": settings.tmdb_api_key, "language": "es-ES"},
        timeout=10,
    )
    # 404 means the season doesn't exist yet — not an error, just not announced
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json().get("air_date")


def check_release(query: str, media_type: str) -> tuple[bool, str]:
    """
    Checks whether a movie or TV show (or specific season) has been released.

    Args:
        query: search term e.g. "Severance temporada 3" or "Mission Impossible 8"
        media_type: "movie" or "tv"

    Returns:
        A tuple of (condition_met, status_message)
        condition_met is True if the title has already been released
        status_message describes the current state in human-readable form
    """
    today = datetime.now(timezone.utc).date()

    # Extract season info before cleaning the query
    season_number = extract_season_number(query)

    # Clean the query so TMDB can find the title
    search_query = clean_query(query) if season_number else query
    item = search_tmdb(search_query, media_type)

    if not item:
        return False, f"No encontré ningún resultado para '{query}'"

    if media_type == "movie":
        title = item.get("title", query)
        release_date_str = item.get("release_date")
    else:
        title = item.get("name", query)

        if season_number:
            # Fetch the specific season's air date
            tmdb_id = item["id"]
            release_date_str = get_season_air_date(tmdb_id, season_number)
            title = f"{title} - Temporada {season_number}"
        else:
            # No season specified — use the show's original air date
            release_date_str = item.get("first_air_date")

    if not release_date_str:
        return False, f"'{title}' no tiene fecha de estreno confirmada todavía"

    release_date = datetime.strptime(release_date_str, "%Y-%m-%d").date()

    if release_date <= today:
        return True, f"'{title}' ya está disponible (estrenó el {release_date.strftime('%d/%m/%Y')})"
    else:
        days_remaining = (release_date - today).days
        return False, f"'{title}' estrena el {release_date.strftime('%d/%m/%Y')} (en {days_remaining} días)"