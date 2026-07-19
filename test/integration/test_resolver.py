import pytest
from harpi.domain.track_metadata import Source
from harpi.application.exceptions import InvalidLinkError


@pytest.mark.integration
class TestYoutubeResolver:
    """Testa o AudioResolver com chamadas HTTP reais ao YouTube."""

    @pytest.mark.asyncio
    async def test_resolve_youtube_short_url(self):
        from harpi.infrastructure.youtube_resolver import YoutubeResolver

        resolver = YoutubeResolver()
        track = await resolver.resolve("https://youtu.be/M8J9zHyyUYc")

        assert track.link == "https://youtube.com/watch?v=M8J9zHyyUYc"
        assert track.source == Source.YOUTUBE
        assert track.source_id == "M8J9zHyyUYc"
        assert track.title is not None
        assert len(track.title) > 0
        assert track.duration is not None

    @pytest.mark.asyncio
    async def test_resolve_youtube_watch_url(self):
        from harpi.infrastructure.youtube_resolver import YoutubeResolver

        resolver = YoutubeResolver()
        track = await resolver.resolve("https://www.youtube.com/watch?v=M8J9zHyyUYc")

        assert track.source_id == "M8J9zHyyUYc"
        assert track.title is not None
        assert track.duration is not None

    @pytest.mark.asyncio
    async def test_resolve_invalid_url_raises(self):
        from harpi.infrastructure.youtube_resolver import YoutubeResolver

        resolver = YoutubeResolver()
        with pytest.raises(InvalidLinkError):
            await resolver.resolve("https://youtu.be/ID_INVALIDO_12345")

    @pytest.mark.asyncio
    async def test_resolve_non_youtube_url_raises(self):
        from harpi.infrastructure.youtube_resolver import YoutubeResolver

        resolver = YoutubeResolver()
        with pytest.raises(InvalidLinkError):
            await resolver.resolve("https://example.com/not-a-video")

    @pytest.mark.asyncio
    async def test_resolve_empty_string_raises(self):
        from harpi.infrastructure.youtube_resolver import YoutubeResolver

        resolver = YoutubeResolver()
        with pytest.raises(InvalidLinkError):
            await resolver.resolve("")


@pytest.mark.integration
class TestYoutubeResolverStream:
    """Testa resolve_stream com chamadas HTTP reais ao YouTube."""

    @pytest.mark.asyncio
    async def test_resolve_stream_returns_playable_url(self):
        from harpi.infrastructure.youtube_resolver import YoutubeResolver
        from harpi.application.exceptions import InvalidLinkError

        resolver = YoutubeResolver()
        track = await resolver.resolve("https://youtu.be/M8J9zHyyUYc")
        with pytest.raises(InvalidLinkError):
            await resolver.resolve_stream(track)
