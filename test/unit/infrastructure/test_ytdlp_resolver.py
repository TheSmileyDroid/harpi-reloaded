import asyncio

import pytest

from harpi.application.exceptions import (
    InvalidLinkError,
    NetworkError,
    ResolutionTimeoutError,
)
from harpi.domain.track_metadata import Source, TrackMetadata
from harpi.infrastructure.ytdlp_resolver import YtDlpResolver


class FakeYtDlp:
    """Simulates yt_dlp.YoutubeDL for testing."""

    def __init__(self, params: dict | None = None):
        self.params = params or {}
        self._title: str | None = "Test Video from yt-dlp"
        self._duration: int | None = 240
        self._extract_info_error: Exception | None = None

    def extract_info(self, url: str, download: bool = True) -> dict:
        if self._extract_info_error:
            raise self._extract_info_error
        # yt-dlp typically returns the canonical watch URL format
        watch_url = "https://www.youtube.com/watch?v=abc"
        return {
            "title": self._title,
            "duration": self._duration,
            "webpage_url": watch_url,
        }


class FakeYtDlpWithFormats(FakeYtDlp):
    """FakeYtDlp that returns a formats list with audio URLs."""

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self._audio_url: str = "https://example.com/audio.m4a"
        self._formats: list[dict] | None = None

    def extract_info(self, url: str, download: bool = True) -> dict:
        info = super().extract_info(url, download)
        if self._formats is not None:
            info["formats"] = self._formats
        else:
            info["formats"] = [
                {
                    "format_id": "140",
                    "ext": "m4a",
                    "url": self._audio_url,
                    "abr": 128,
                    "vcodec": "none",
                    "acodec": "mp4a.40.2",
                },
                {
                    "format_id": "251",
                    "ext": "webm",
                    "url": self._audio_url,
                    "abr": 160,
                    "vcodec": "none",
                    "acodec": "opus",
                },
            ]
        # Only set top-level url when there are real playable audio formats
        has_playable = any(
            f.get("vcodec") == "none"
            and f.get("acodec") not in (None, "none")
            and isinstance(f.get("url"), str)
            for f in info["formats"]
        )
        if has_playable:
            info["url"] = self._audio_url
        return info


class FakeYtDlpNoUrl(FakeYtDlp):
    """FakeYtDlp that does NOT set top-level url — simulates edge cases."""

    def extract_info(self, url: str, download: bool = True) -> dict:
        info = super().extract_info(url, download)
        # No top-level url set; only formats are present
        info["formats"] = [
            {
                "format_id": "140",
                "ext": "m4a",
                "url": "https://example.com/fallback_audio.m4a",
                "abr": 128,
                "vcodec": "none",
                "acodec": "mp4a.40.2",
            },
        ]
        return info


class FakeYtDlpFactory:
    def __init__(self, instances: list[FakeYtDlp] | None = None):
        self._instances = instances or []
        self._call_index = 0

    def __call__(self, params: dict | None = None) -> FakeYtDlp:
        if self._call_index < len(self._instances):
            inst = self._instances[self._call_index]
            self._call_index += 1
            return inst
        return FakeYtDlp(params)


def _make_resolver(*instances: FakeYtDlp) -> YtDlpResolver:
    factory = FakeYtDlpFactory(list(instances))
    return YtDlpResolver(ytdlp_factory=factory)


class TestIsYoutubeUrl:
    def test_youtube_com(self):
        assert (
            YtDlpResolver._is_youtube_url("https://www.youtube.com/watch?v=abc") is True
        )

    def test_youtu_be(self):
        assert YtDlpResolver._is_youtube_url("https://youtu.be/abc") is True

    def test_non_youtube(self):
        assert YtDlpResolver._is_youtube_url("https://example.com/video") is False

    def test_empty_string(self):
        assert YtDlpResolver._is_youtube_url("") is False


class TestResolve:
    async def test_empty_string_raises(self):
        r = YtDlpResolver()
        with pytest.raises(InvalidLinkError, match="empty"):
            await r.resolve("")

    async def test_whitespace_only_raises(self):
        r = YtDlpResolver()
        with pytest.raises(InvalidLinkError, match="empty"):
            await r.resolve("   ")

    async def test_non_youtube_url_raises(self):
        r = YtDlpResolver()
        with pytest.raises(InvalidLinkError, match="Not a YouTube URL"):
            await r.resolve("https://example.com/video")

    async def test_success(self):
        yt = FakeYtDlp(params={"quiet": True})
        r = _make_resolver(yt)

        result = await r.resolve("https://youtu.be/abc")

        assert result.title == "Test Video from yt-dlp"
        assert result.duration == 240
        assert result.source == Source.YOUTUBE
        assert "youtube.com/watch?v=abc" in result.link

    async def test_supports_youtube_com_url(self):
        yt = FakeYtDlp()
        r = _make_resolver(yt)

        result = await r.resolve("https://www.youtube.com/watch?v=abc")

        assert result.title == "Test Video from yt-dlp"
        assert result.duration == 240
        assert result.source == Source.YOUTUBE
        assert result.link == "https://www.youtube.com/watch?v=abc"

    async def test_title_none_raises(self):
        yt = FakeYtDlp()
        yt._title = None
        r = _make_resolver(yt)

        with pytest.raises(InvalidLinkError, match="Could not resolve video title"):
            await r.resolve("https://youtu.be/abc")

    async def test_resolve_timeout(self):
        yt = FakeYtDlp()
        yt._extract_info_error = asyncio.TimeoutError()
        r = _make_resolver(yt)

        with pytest.raises(ResolutionTimeoutError):
            await r.resolve("https://youtu.be/abc")

    async def test_resolve_download_error_becomes_invalid_link(self):
        from yt_dlp import DownloadError

        yt = FakeYtDlp()
        yt._extract_info_error = DownloadError("HTTP Error 404: Not Found")
        r = _make_resolver(yt)

        with pytest.raises(InvalidLinkError):
            await r.resolve("https://youtu.be/abc")

    async def test_resolve_download_error_private_video(self):
        from yt_dlp import DownloadError

        yt = FakeYtDlp()
        yt._extract_info_error = DownloadError("Private video")
        r = _make_resolver(yt)

        with pytest.raises(InvalidLinkError):
            await r.resolve("https://youtu.be/abc")

    async def test_resolve_network_error(self):
        from yt_dlp.utils import ExtractorError

        yt = FakeYtDlp()
        yt._extract_info_error = ExtractorError("Connection refused")
        r = _make_resolver(yt)

        with pytest.raises(NetworkError):
            await r.resolve("https://youtu.be/abc")

    async def test_resolve_generic_exception_becomes_network_error(self):
        yt = FakeYtDlp()
        yt._extract_info_error = RuntimeError("Unexpected error")
        r = _make_resolver(yt)

        with pytest.raises(NetworkError):
            await r.resolve("https://youtu.be/abc")

    async def test_cookiefile_passed_to_factory(self):
        """Ensure cookiefile is included in params dict."""
        r = YtDlpResolver(cookiefile="/tmp/cookies.txt")

        # The default factory is yt_dlp.YoutubeDL, which we can't easily
        # test without mocking. We verify at the integration/functional level
        # that the cookiefile param is accepted.
        assert r._cookiefile == "/tmp/cookies.txt"


class TestResolveStream:
    async def test_success_via_top_level_url(self):
        """Uses the top-level url field (the main yt-dlp path)."""
        yt = FakeYtDlpWithFormats()
        r = _make_resolver(yt)
        track = TrackMetadata(
            link="https://youtu.be/abc",
            title="Test",
            duration=240,
            source=Source.YOUTUBE,
        )

        result = await r.resolve_stream(track)

        assert result == "https://example.com/audio.m4a"

    async def test_success_via_formats_fallback(self):
        """Falls back to iterating formats when top-level url is absent."""
        yt = FakeYtDlpNoUrl()
        r = _make_resolver(yt)
        track = TrackMetadata(
            link="https://youtu.be/abc",
            title="Test",
            duration=240,
            source=Source.YOUTUBE,
        )

        result = await r.resolve_stream(track)

        assert result == "https://example.com/fallback_audio.m4a"

    async def test_no_formats_raises(self):
        yt = FakeYtDlpWithFormats()
        yt._formats = []
        r = _make_resolver(yt)
        track = TrackMetadata(
            link="https://youtu.be/abc",
            title="Test",
            duration=240,
            source=Source.YOUTUBE,
        )

        with pytest.raises(InvalidLinkError, match="No audio stream"):
            await r.resolve_stream(track)

    async def test_no_playable_format_raises(self):
        yt = FakeYtDlpWithFormats()
        yt._formats = [
            {
                "format_id": "18",
                "ext": "mp4",
                "url": None,
                "vcodec": "avc1.42001E",
                "acodec": "mp4a.40.2",
            },
        ]
        r = _make_resolver(yt)
        track = TrackMetadata(
            link="https://youtu.be/abc",
            title="Test",
            duration=240,
            source=Source.YOUTUBE,
        )

        with pytest.raises(InvalidLinkError, match="No audio stream"):
            await r.resolve_stream(track)

    async def test_stream_timeout(self):
        yt = FakeYtDlpWithFormats()
        yt._extract_info_error = asyncio.TimeoutError()
        r = _make_resolver(yt)
        track = TrackMetadata(
            link="https://youtu.be/abc",
            title="Test",
            duration=240,
            source=Source.YOUTUBE,
        )

        with pytest.raises(ResolutionTimeoutError):
            await r.resolve_stream(track)

    async def test_stream_download_error(self):
        from yt_dlp import DownloadError

        yt = FakeYtDlpWithFormats()
        yt._extract_info_error = DownloadError("HTTP Error 403: Forbidden")
        r = _make_resolver(yt)
        track = TrackMetadata(
            link="https://youtu.be/abc",
            title="Test",
            duration=240,
            source=Source.YOUTUBE,
        )

        with pytest.raises(InvalidLinkError):
            await r.resolve_stream(track)

    async def test_stream_network_error(self):
        from yt_dlp.utils import ExtractorError

        yt = FakeYtDlpWithFormats()
        yt._extract_info_error = ExtractorError("Network is unreachable")
        r = _make_resolver(yt)
        track = TrackMetadata(
            link="https://youtu.be/abc",
            title="Test",
            duration=240,
            source=Source.YOUTUBE,
        )

        with pytest.raises(NetworkError):
            await r.resolve_stream(track)


class TestAuthErrors:
    """Tests for authentication-related error handling."""

    async def test_sign_in_error_gives_helpful_message(self):
        from yt_dlp import DownloadError

        yt = FakeYtDlp()
        yt._extract_info_error = DownloadError(
            "ERROR: [youtube] abc123: Sign in to confirm you're not a bot."
        )
        r = _make_resolver(yt)

        with pytest.raises(InvalidLinkError) as exc:
            await r.resolve("https://youtu.be/abc")

        msg = str(exc.value)
        assert "bot check" in msg
        assert "YT_DLP_COOKIES_FILE" in msg

    async def test_non_auth_download_error_still_raises(self):
        from yt_dlp import DownloadError

        yt = FakeYtDlp()
        yt._extract_info_error = DownloadError("HTTP Error 404: Not Found")
        r = _make_resolver(yt)

        with pytest.raises(InvalidLinkError) as exc:
            await r.resolve("https://youtu.be/abc")

        assert "bot check" not in str(exc.value)
