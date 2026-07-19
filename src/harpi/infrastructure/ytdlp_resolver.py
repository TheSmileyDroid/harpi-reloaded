import asyncio
import logging
import os
from collections.abc import Callable

import yt_dlp
from yt_dlp.utils import ExtractorError

from harpi.domain.track_metadata import TrackMetadata, Source
from harpi.application.ports.audio import AudioResolverProtocol
from harpi.application.exceptions import (
    InvalidLinkError,
    NetworkError,
    ResolutionTimeoutError,
)

logger = logging.getLogger(__name__)


class YtDlpResolver(AudioResolverProtocol):
    """Resolver that uses yt-dlp as a Python library to extract YouTube metadata and audio streams.

    Serves as a fallback when pytubefix fails (e.g., datacenter IP blocks, PO Token issues).
    Supports cookies.txt for authenticated access.
    """

    TIMEOUT = 30

    def __init__(
        self,
        ytdlp_factory: Callable | None = None,
        cookiefile: str | None = None,
    ):
        self._factory = ytdlp_factory or yt_dlp.YoutubeDL
        self._cookiefile = cookiefile or os.environ.get("YT_DLP_COOKIES_FILE")

    async def resolve(self, link: str) -> TrackMetadata:
        if not link or not link.strip():
            raise InvalidLinkError("Link is empty")

        if not self._is_youtube_url(link):
            raise InvalidLinkError(f"Not a YouTube URL: {link}")

        info = await self._extract_info(link)

        title = info.get("title")
        if title is None:
            raise InvalidLinkError("Could not resolve video title")

        duration = info.get("duration")
        watch_url = info.get("webpage_url", link)

        return TrackMetadata(
            link=watch_url,
            title=title,
            duration=duration,
            source=Source.YOUTUBE,
        )

    async def resolve_stream(self, track: TrackMetadata) -> str:
        info = await self._extract_info(track.link)

        # yt-dlp puts the selected format's direct URL at the top level
        url: object = info.get("url")
        if isinstance(url, str):
            return url

        # Fallback: find an audio-only format with a real audio codec
        formats = info.get("formats") or []
        audio_only = [
            f
            for f in formats
            if f.get("vcodec") == "none"
            and f.get("acodec") not in (None, "none")
            and isinstance(f.get("url"), str)
        ]
        if audio_only:
            # Last format tends to be the highest quality
            return audio_only[-1]["url"]

        # Desperate fallback: first format with a URL
        for f in formats:
            url = f.get("url")
            if isinstance(url, str):
                return url

        raise InvalidLinkError(f"No audio stream available for {track.link}")

    async def _extract_info(self, url: str) -> dict:
        opts = {
            "quiet": True,
            "format": "bestaudio/best",
            "no_warnings": True,
        }
        if self._cookiefile:
            opts["cookiefile"] = self._cookiefile

        def _sync_extract() -> dict:
            ydl = self._factory(params=opts)
            return ydl.extract_info(url, download=False)

        try:
            info = await asyncio.wait_for(
                asyncio.to_thread(_sync_extract),
                timeout=self.TIMEOUT,
            )
        except asyncio.TimeoutError as e:
            raise ResolutionTimeoutError(
                f"Resolution timed out after {self.TIMEOUT}s"
            ) from e
        except yt_dlp.DownloadError as e:
            msg = str(e)
            if "Sign in to confirm" in msg:
                raise InvalidLinkError(
                    "YouTube requires authentication (bot check). "
                    "Export a cookies.txt file from your browser and set the "
                    "YT_DLP_COOKIES_FILE environment variable to its path. "
                    "See: https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp"
                ) from e
            raise InvalidLinkError(msg) from e
        except ExtractorError as e:
            raise NetworkError(str(e)) from e
        except Exception as e:
            raise NetworkError(str(e)) from e

        return info

    @staticmethod
    def _is_youtube_url(link: str) -> bool:
        return "youtube.com" in link or "youtu.be" in link
