import asyncio
from collections.abc import Callable

from pytubefix.async_youtube import AsyncYouTube
from pytubefix.exceptions import (
    RegexMatchError,
    VideoUnavailable,
    VideoPrivate,
    MaxRetriesExceeded,
)

from harpi.domain.track_metadata import TrackMetadata, Source
from harpi.application.ports.audio import AudioResolverProtocol
from harpi.application.exceptions import (
    InvalidLinkError,
    NetworkError,
    ResolutionTimeoutError,
)


class YoutubeResolver(AudioResolverProtocol):
    TIMEOUT = 15

    def __init__(self, youtube_factory: Callable | None = None):
        self._youtube_factory = youtube_factory or AsyncYouTube

    async def resolve(self, link: str) -> TrackMetadata:
        if not link or not link.strip():
            raise InvalidLinkError("Link is empty")

        if not self._is_youtube_url(link):
            raise InvalidLinkError(f"Not a YouTube URL: {link}")

        title, duration, watch_url = await self._fetch_metadata(link)

        if title is None:
            raise InvalidLinkError("Could not resolve video title")

        return TrackMetadata(
            link=watch_url,
            title=title,
            duration=duration,
            source=Source.YOUTUBE,
        )

    async def resolve_stream(self, track: TrackMetadata) -> str:
        try:
            # WEB retorna URLs SABR que o FFmpeg não consegue abrir; ANDROID_VR
            # serve stream direto sem exigir PO Token.
            yt = self._youtube_factory(track.link, "ANDROID_VR")
        except RegexMatchError as e:
            raise InvalidLinkError(str(e)) from e

        try:
            streams = await asyncio.wait_for(yt.streams(), timeout=self.TIMEOUT)
        except asyncio.TimeoutError as e:
            raise ResolutionTimeoutError(
                f"Stream resolution timed out after {self.TIMEOUT}s"
            ) from e
        except (VideoUnavailable, VideoPrivate, RegexMatchError) as e:
            raise InvalidLinkError(str(e)) from e
        except (MaxRetriesExceeded, OSError) as e:
            raise NetworkError(str(e)) from e

        stream = streams.get_audio_only()
        if stream is None:
            raise InvalidLinkError(f"No audio stream available for {track.link}")
        return stream.url

    async def _fetch_metadata(self, link: str) -> tuple[str | None, int | None, str]:
        try:
            yt = self._youtube_factory(link, "ANDROID_VR")
        except RegexMatchError as e:
            raise InvalidLinkError(str(e)) from e

        try:
            title = await asyncio.wait_for(yt.title(), timeout=self.TIMEOUT)
            duration = await asyncio.wait_for(yt.length(), timeout=self.TIMEOUT)
        except asyncio.TimeoutError as e:
            raise ResolutionTimeoutError(
                f"Resolution timed out after {self.TIMEOUT}s"
            ) from e
        except (VideoUnavailable, VideoPrivate, RegexMatchError) as e:
            raise InvalidLinkError(str(e)) from e
        except (MaxRetriesExceeded, OSError) as e:
            raise NetworkError(str(e)) from e

        return title, duration, yt.watch_url

    @staticmethod
    def _is_youtube_url(link: str) -> bool:
        return "youtube.com" in link or "youtu.be" in link
