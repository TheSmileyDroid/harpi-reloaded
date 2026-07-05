import asyncio

import pytest
from pytubefix.exceptions import (
    RegexMatchError,
    VideoUnavailable,
    VideoPrivate,
    MaxRetriesExceeded,
)

from harpi.application.exceptions import (
    InvalidLinkError,
    NetworkError,
    ResolutionTimeoutError,
)
from harpi.domain.track_metadata import Source, TrackMetadata
from harpi.infrastructure.youtube_resolver import YoutubeResolver


class FakeStream:
    def __init__(self, url: str):
        self.url = url


class FakeStreams:
    def __init__(self, audio_stream: FakeStream | None = None):
        self._audio_stream = audio_stream

    def get_audio_only(self) -> FakeStream | None:
        return self._audio_stream


class FakeAsyncYouTube:
    def __init__(
        self,
        link: str,
        client: str = "ANDROID_VR",
    ):
        self.link = link
        self.watch_url = "https://www.youtube.com/watch?v=abc"
        self._title: str | None = "Test Video"
        self._length: int | None = 180
        self._streams: FakeStreams | None = None
        self._title_error: Exception | None = None
        self._length_error: Exception | None = None
        self._streams_error: Exception | None = None
        self._init_error: Exception | None = None

    async def title(self) -> str | None:
        if self._title_error:
            raise self._title_error
        return self._title

    async def length(self) -> int | None:
        if self._length_error:
            raise self._length_error
        return self._length

    async def streams(self) -> FakeStreams:
        if self._streams_error:
            raise self._streams_error
        return self._streams or FakeStreams(FakeStream("http://stream.example.com/audio"))


class FakeAsyncYouTubeFactory:
    def __init__(self, instances: list[FakeAsyncYouTube] | None = None):
        self._instances = instances or []
        self._call_index = 0

    def __call__(self, link: str, client: str = "ANDROID_VR") -> FakeAsyncYouTube:
        if self._call_index < len(self._instances):
            inst = self._instances[self._call_index]
            self._call_index += 1
            return inst
        raise RegexMatchError(caller="__init__", pattern="")


@pytest.fixture
def resolver():
    return YoutubeResolver()


def _make_resolver(*instances: FakeAsyncYouTube) -> YoutubeResolver:
    factory = FakeAsyncYouTubeFactory(list(instances))
    return YoutubeResolver(youtube_factory=factory)


class TestIsYoutubeUrl:
    def test_youtube_com(self, resolver):
        assert resolver._is_youtube_url("https://www.youtube.com/watch?v=abc") is True

    def test_youtu_be(self, resolver):
        assert resolver._is_youtube_url("https://youtu.be/abc") is True

    def test_non_youtube(self, resolver):
        assert resolver._is_youtube_url("https://example.com/video") is False

    def test_empty_string(self, resolver):
        assert resolver._is_youtube_url("") is False


class TestResolve:
    async def test_empty_string_raises(self, resolver):
        with pytest.raises(InvalidLinkError, match="empty"):
            await resolver.resolve("")

    async def test_whitespace_only_raises(self, resolver):
        with pytest.raises(InvalidLinkError, match="empty"):
            await resolver.resolve("   ")

    async def test_non_youtube_url_raises(self, resolver):
        with pytest.raises(InvalidLinkError, match="Not a YouTube URL"):
            await resolver.resolve("https://example.com/video")

    async def test_success(self):
        yt = FakeAsyncYouTube("https://youtu.be/abc")
        r = _make_resolver(yt)

        result = await r.resolve("https://youtu.be/abc")

        assert result.title == "Test Video"
        assert result.duration == 180
        assert result.source == Source.YOUTUBE
        assert result.link == "https://www.youtube.com/watch?v=abc"

    async def test_title_none_raises(self):
        yt = FakeAsyncYouTube("https://youtu.be/abc")
        yt._title = None
        r = _make_resolver(yt)

        with pytest.raises(InvalidLinkError, match="Could not resolve video title"):
            await r.resolve("https://youtu.be/abc")

    async def test_metadata_timeout(self):
        yt = FakeAsyncYouTube("https://youtu.be/abc")
        yt._title_error = asyncio.TimeoutError()
        r = _make_resolver(yt)

        with pytest.raises(ResolutionTimeoutError):
            await r.resolve("https://youtu.be/abc")

    async def test_metadata_video_unavailable(self):
        yt = FakeAsyncYouTube("https://youtu.be/abc")
        yt._title_error = VideoUnavailable("video")
        r = _make_resolver(yt)

        with pytest.raises(InvalidLinkError):
            await r.resolve("https://youtu.be/abc")

    async def test_metadata_video_private(self):
        yt = FakeAsyncYouTube("https://youtu.be/abc")
        yt._title_error = VideoPrivate("video")
        r = _make_resolver(yt)

        with pytest.raises(InvalidLinkError):
            await r.resolve("https://youtu.be/abc")

    async def test_metadata_regex_error(self):
        yt = FakeAsyncYouTube("https://youtu.be/abc")
        yt._title_error = RegexMatchError(caller="title", pattern="")
        r = _make_resolver(yt)

        with pytest.raises(InvalidLinkError):
            await r.resolve("https://youtu.be/abc")

    async def test_metadata_network_error(self):
        yt = FakeAsyncYouTube("https://youtu.be/abc")
        yt._title_error = MaxRetriesExceeded()
        r = _make_resolver(yt)

        with pytest.raises(NetworkError):
            await r.resolve("https://youtu.be/abc")

    async def test_metadata_os_error(self):
        yt = FakeAsyncYouTube("https://youtu.be/abc")
        yt._title_error = OSError("connection refused")
        r = _make_resolver(yt)

        with pytest.raises(NetworkError):
            await r.resolve("https://youtu.be/abc")


class TestResolveStream:
    async def test_success(self):
        yt = FakeAsyncYouTube("https://youtu.be/abc")
        r = _make_resolver(yt)
        track = TrackMetadata(
            link="https://youtu.be/abc",
            title="Test",
            duration=120,
            source=Source.YOUTUBE,
        )

        result = await r.resolve_stream(track)

        assert result == "http://stream.example.com/audio"

    async def test_regex_error_on_init(self):
        def _raising_factory(link: str, client: str = "ANDROID_VR"):
            raise RegexMatchError(caller="streams", pattern="")

        r = YoutubeResolver(youtube_factory=_raising_factory)
        track = TrackMetadata(
            link="https://youtu.be/abc",
            title="Test",
            duration=120,
            source=Source.YOUTUBE,
        )

        with pytest.raises(InvalidLinkError):
            await r.resolve_stream(track)

    async def test_timeout(self):
        yt = FakeAsyncYouTube("https://youtu.be/abc")
        yt._streams_error = asyncio.TimeoutError()
        r = _make_resolver(yt)
        track = TrackMetadata(
            link="https://youtu.be/abc",
            title="Test",
            duration=120,
            source=Source.YOUTUBE,
        )

        with pytest.raises(ResolutionTimeoutError):
            await r.resolve_stream(track)

    async def test_video_unavailable(self):
        yt = FakeAsyncYouTube("https://youtu.be/abc")
        yt._streams_error = VideoUnavailable("video")
        r = _make_resolver(yt)
        track = TrackMetadata(
            link="https://youtu.be/abc",
            title="Test",
            duration=120,
            source=Source.YOUTUBE,
        )

        with pytest.raises(InvalidLinkError):
            await r.resolve_stream(track)

    async def test_video_private(self):
        yt = FakeAsyncYouTube("https://youtu.be/abc")
        yt._streams_error = VideoPrivate("video")
        r = _make_resolver(yt)
        track = TrackMetadata(
            link="https://youtu.be/abc",
            title="Test",
            duration=120,
            source=Source.YOUTUBE,
        )

        with pytest.raises(InvalidLinkError):
            await r.resolve_stream(track)

    async def test_regex_error_on_streams(self):
        yt = FakeAsyncYouTube("https://youtu.be/abc")
        yt._streams_error = RegexMatchError(caller="streams", pattern="")
        r = _make_resolver(yt)
        track = TrackMetadata(
            link="https://youtu.be/abc",
            title="Test",
            duration=120,
            source=Source.YOUTUBE,
        )

        with pytest.raises(InvalidLinkError):
            await r.resolve_stream(track)

    async def test_max_retries_exceeded(self):
        yt = FakeAsyncYouTube("https://youtu.be/abc")
        yt._streams_error = MaxRetriesExceeded()
        r = _make_resolver(yt)
        track = TrackMetadata(
            link="https://youtu.be/abc",
            title="Test",
            duration=120,
            source=Source.YOUTUBE,
        )

        with pytest.raises(NetworkError):
            await r.resolve_stream(track)

    async def test_os_error(self):
        yt = FakeAsyncYouTube("https://youtu.be/abc")
        yt._streams_error = OSError("connection refused")
        r = _make_resolver(yt)
        track = TrackMetadata(
            link="https://youtu.be/abc",
            title="Test",
            duration=120,
            source=Source.YOUTUBE,
        )

        with pytest.raises(NetworkError):
            await r.resolve_stream(track)

    async def test_no_audio_stream(self):
        yt = FakeAsyncYouTube("https://youtu.be/abc")
        yt._streams = FakeStreams(audio_stream=None)
        r = _make_resolver(yt)
        track = TrackMetadata(
            link="https://youtu.be/abc",
            title="Test",
            duration=120,
            source=Source.YOUTUBE,
        )

        with pytest.raises(InvalidLinkError, match="No audio stream"):
            await r.resolve_stream(track)
