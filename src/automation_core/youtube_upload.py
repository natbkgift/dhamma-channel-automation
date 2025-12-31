from __future__ import annotations

import os
from pathlib import Path


class YoutubeUploadError(Exception):
    """Base error for YouTube upload failures."""


class YoutubeDepsMissingError(YoutubeUploadError):
    """Raised when Google API dependencies are missing."""


class YoutubeAuthMissingError(YoutubeUploadError):
    """Raised when required auth environment variables are missing."""


class YoutubeApiError(YoutubeUploadError):
    """Raised when the YouTube API returns an error."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise YoutubeAuthMissingError(
            f"Missing required YouTube auth environment variable: {name}"
        )
    return value.strip()


def upload_video(
    mp4_path: Path,
    title: str,
    description: str,
    tags: list[str],
    privacy_status: str,
) -> str:
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaFileUpload
    except ImportError as exc:
        raise YoutubeDepsMissingError(
            "Google API dependencies are not installed"
        ) from exc

    client_id = _require_env("YOUTUBE_CLIENT_ID")
    client_secret = _require_env("YOUTUBE_CLIENT_SECRET")
    refresh_token = _require_env("YOUTUBE_REFRESH_TOKEN")

    scopes = ["https://www.googleapis.com/auth/youtube.upload"]
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=scopes,
    )

    try:
        creds.refresh(Request())
    except Exception as exc:
        raise YoutubeApiError("YouTube auth refresh failed") from exc

    try:
        youtube = build("youtube", "v3", credentials=creds)
    except Exception as exc:
        raise YoutubeApiError("YouTube client initialization failed") from exc

    safe_tags = [tag for tag in tags if isinstance(tag, str)] if tags else []
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": safe_tags,
        },
        "status": {
            "privacyStatus": privacy_status,
        },
    }

    media = MediaFileUpload(str(mp4_path), mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media
    )
    try:
        response = request.execute()
    except HttpError as exc:
        status = getattr(getattr(exc, "resp", None), "status", None)
        raise YoutubeApiError("YouTube API request failed", status=status) from exc
    except Exception as exc:
        raise YoutubeApiError("YouTube upload failed") from exc

    video_id = None
    if isinstance(response, dict):
        video_id = response.get("id")

    if not isinstance(video_id, str) or not video_id:
        raise YoutubeApiError("YouTube API response missing video id")

    return video_id
