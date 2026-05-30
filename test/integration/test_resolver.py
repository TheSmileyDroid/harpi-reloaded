import pytest
from harpi.domain.track import Source


@pytest.mark.integration
class TestYoutubeResolver:
    """Testa o AudioResolver com chamadas HTTP reais ao YouTube."""

    @pytest.mark.asyncio
    async def test_resolve_youtube_short_url(self):
        from harpi.infrastructure.youtube_resolver import YoutubeResolver

        resolver = YoutubeResolver()
        track = await resolver.resolve("https://youtu.be/jNQXAC9IVRw")

        assert track.link == "https://youtube.com/watch?v=jNQXAC9IVRw"
        assert track.source == Source.YOUTUBE
        assert track.source_id == "jNQXAC9IVRw"
        assert track.title is not None
        assert len(track.title) > 0
        assert track.duration is not None
        assert track.duration > 0
        assert track.resolved is True

    @pytest.mark.asyncio
    async def test_resolve_youtube_watch_url(self):
        from harpi.infrastructure.youtube_resolver import YoutubeResolver

        resolver = YoutubeResolver()
        track = await resolver.resolve("https://www.youtube.com/watch?v=jNQXAC9IVRw")

        assert track.source_id == "jNQXAC9IVRw"
        assert track.title is not None
        assert track.duration is not None

    @pytest.mark.asyncio
    async def test_resolve_invalid_url_raises(self):
        from harpi.infrastructure.youtube_resolver import YoutubeResolver

        resolver = YoutubeResolver()
        with pytest.raises(Exception):
            await resolver.resolve("https://youtu.be/ID_INVALIDO_12345")

    @pytest.mark.asyncio
    async def test_resolve_non_youtube_url_raises(self):
        from harpi.infrastructure.youtube_resolver import YoutubeResolver

        resolver = YoutubeResolver()
        with pytest.raises(Exception):
            await resolver.resolve("https://example.com/not-a-video")

    @pytest.mark.asyncio
    async def test_resolve_empty_string_raises(self):
        from harpi.infrastructure.youtube_resolver import YoutubeResolver

        resolver = YoutubeResolver()
        with pytest.raises(Exception):
            await resolver.resolve("")
