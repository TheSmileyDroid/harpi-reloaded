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
        js_runtimes: dict[str, dict] | None = None,
    ):
        self._factory = ytdlp_factory or yt_dlp.YoutubeDL
        self._cookiefile = cookiefile or os.environ.get("YT_DLP_COOKIES_FILE")
        self._js_runtimes = js_runtimes
        self._last_stream_headers: dict[str, str] = {}

    async def resolve(self, link: str) -> TrackMetadata:
        if not link or not link.strip():
            raise InvalidLinkError("Link is empty")

        if not self._is_youtube_url(link):
            raise InvalidLinkError(f"Not a YouTube URL: {link}")

        info = await self._extract_info(link, metadata_only=True)

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
        info = await self._extract_info(track.link, metadata_only=False)

        url: object = info.get("url")
        if isinstance(url, str):
            self._last_stream_headers = info.get("http_headers", {})
            logger.info(
                "Resolved stream URL: format=%s ext=%s acodec=%s abr=%s",
                info.get("format_id", "unknown"),
                info.get("ext", "unknown"),
                info.get("acodec", "unknown"),
                info.get("abr", "unknown"),
            )
            logger.info("Stream URL: %s...", url[:80])
            logger.info(
                "Stream HTTP headers: %s", list(self._last_stream_headers.keys())
            )
            return url

        formats = info.get("formats", [])
        logger.info("Available formats: %d", len(formats))
        for f in formats:
            if f.get("vcodec") != "none":
                continue
            acodec = f.get("acodec")
            if acodec is None or acodec == "none":
                continue
            fmt_url = f.get("url")
            if isinstance(fmt_url, str):
                self._last_stream_headers = f.get("http_headers", {})
                logger.info(
                    "Resolved stream URL (fallback): format=%s ext=%s acodec=%s",
                    f.get("format_id", "unknown"),
                    f.get("ext", "unknown"),
                    f.get("acodec", "unknown"),
                )
                return fmt_url

        raise InvalidLinkError(f"No audio stream available for {track.link}")

    def get_last_stream_headers(self) -> dict[str, str]:
        """Return HTTP headers needed for the last resolved stream URL."""
        return self._last_stream_headers.copy()

    def get_cookiefile(self) -> str | None:
        return self._cookiefile

    async def _extract_info(self, url: str, metadata_only: bool = False) -> dict:
        opts: dict = {
            "quiet": True,
            "no_warnings": True,
        }
        if not metadata_only:
            opts["format"] = "m4a/bestaudio/best"
        if self._cookiefile:
            logger.info("Using cookiefile: %s", self._cookiefile)
            opts["cookiefile"] = self._cookiefile
        else:
            logger.warning("No cookiefile configured — YouTube may require cookies")
        if self._js_runtimes:
            opts["js_runtimes"] = self._js_runtimes

        def _sync_extract() -> dict:
            ydl = self._factory(params=opts)
            if self._cookiefile:
                self._log_cookie_stats(ydl)
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
                    "YouTube bot check triggered from this IP. "
                    "A cookies.txt file was provided but may lack required auth cookies. "
                    "Export fresh cookies from a logged-in browser using: "
                    "yt-dlp --cookies-from-browser chrome --cookies cookies.txt\n"
                    "Then copy the file to the server and set YT_DLP_COOKIES_FILE.\n"
                    "See: https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp"
                ) from e
            raise InvalidLinkError(msg) from e
        except ExtractorError as e:
            raise NetworkError(str(e)) from e
        except Exception as e:
            raise NetworkError(str(e)) from e

        return info

    @staticmethod
    def _log_cookie_stats(ydl: yt_dlp.YoutubeDL) -> None:
        """Log how many cookies were loaded for youtube.com."""
        try:
            from unittest.mock import ANY

            _ = ANY
        except ImportError:
            pass
        try:
            jar = getattr(ydl, "cookiejar", None)
            if jar is not None:
                yt_cookies = [c for c in jar if c.domain and "youtube.com" in c.domain]
                names = sorted(c.name for c in yt_cookies)
                logger.info(
                    "Loaded %d YouTube cookies: %s",
                    len(yt_cookies),
                    ", ".join(names) if names else "none",
                )
                required = {"LOGIN_INFO", "SAPISID", "__Secure-3PAPISID"}
                missing = required - set(names)
                if missing:
                    logger.warning(
                        "Missing auth cookies: %s. "
                        "y-dlp may still be blocked. "
                        "Re-export cookies from a logged-in browser session.",
                        ", ".join(sorted(missing)),
                    )
        except Exception:
            pass

    @staticmethod
    def _is_youtube_url(link: str) -> bool:
        return "youtube.com" in link or "youtu.be" in link
