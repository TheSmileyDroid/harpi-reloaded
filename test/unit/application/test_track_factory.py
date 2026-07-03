import pytest
from harpi.application.track_factory import TrackFactory
from harpi.domain.track_metadata import TrackMetadata, Source
from harpi.application.exceptions import InvalidLinkError


class FakeResolver:
    def __init__(self) -> None:
        self._failures: dict[str, Exception] = {}

    async def resolve(self, link: str) -> TrackMetadata:
        if link in self._failures:
            raise self._failures[link]
        return TrackMetadata(
            link=link,
            source=Source.YOUTUBE,
            title="Resolved Track",
            duration=180,
        )

    async def resolve_stream(self, track: TrackMetadata) -> str:
        return f"stream://{track.link}"

    def set_failure(self, link: str, exc: Exception) -> None:
        self._failures[link] = exc


class TestTrackFactory:
    @pytest.mark.asyncio
    async def test_create_returns_track_metadata(self):
        resolver = FakeResolver()
        factory = TrackFactory(resolver=resolver)
        result = await factory.create("https://youtu.be/abc")
        assert isinstance(result, TrackMetadata)
        assert result.link == "https://youtu.be/abc"
        assert result.title == "Resolved Track"
        assert result.duration == 180
        assert result.source == Source.YOUTUBE

    @pytest.mark.asyncio
    async def test_create_delegates_to_resolver(self):
        resolver = FakeResolver()
        factory = TrackFactory(resolver=resolver)
        await factory.create("https://youtu.be/test123")
        assert resolver._failures.get("https://youtu.be/test123") is None

    @pytest.mark.asyncio
    async def test_create_propagates_resolver_error(self):
        resolver = FakeResolver()
        resolver.set_failure("https://youtu.be/bad", InvalidLinkError("Bad link"))
        factory = TrackFactory(resolver=resolver)
        with pytest.raises(InvalidLinkError):
            await factory.create("https://youtu.be/bad")

    @pytest.mark.asyncio
    async def test_create_multiple_tracks(self):
        resolver = FakeResolver()
        factory = TrackFactory(resolver=resolver)
        track1 = await factory.create("https://youtu.be/abc")
        track2 = await factory.create("https://youtu.be/def")
        assert track1.link == "https://youtu.be/abc"
        assert track2.link == "https://youtu.be/def"
        assert track1 != track2
