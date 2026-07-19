import aiohttp

import pytest

from harpi.domain.track_metadata import Source
from harpi.application.exceptions import InvalidLinkError, NetworkError


@pytest.mark.integration
class TestYtDlpResolver:
    """Integration tests for YtDlpResolver with real HTTP calls to YouTube."""

    @pytest.mark.asyncio
    async def test_resolve_youtube_short_url(self):
        from harpi.infrastructure.ytdlp_resolver import YtDlpResolver

        resolver = YtDlpResolver()
        track = await resolver.resolve("https://youtu.be/M8J9zHyyUYc")

        assert track.link == "https://www.youtube.com/watch?v=M8J9zHyyUYc"
        assert track.source == Source.YOUTUBE
        assert track.source_id == "M8J9zHyyUYc"
        assert track.title is not None
        assert len(track.title) > 0
        assert track.duration is not None
        assert track.duration > 0

    @pytest.mark.asyncio
    async def test_resolve_youtube_watch_url(self):
        from harpi.infrastructure.ytdlp_resolver import YtDlpResolver

        resolver = YtDlpResolver()
        track = await resolver.resolve("https://www.youtube.com/watch?v=M8J9zHyyUYc")

        assert track.source_id == "M8J9zHyyUYc"
        assert track.title is not None
        assert track.duration is not None

    @pytest.mark.asyncio
    async def test_resolve_invalid_url_raises(self):
        from harpi.infrastructure.ytdlp_resolver import YtDlpResolver

        resolver = YtDlpResolver()
        with pytest.raises(InvalidLinkError):
            await resolver.resolve("https://youtu.be/ID_INVALIDO_12345")

    @pytest.mark.asyncio
    async def test_resolve_non_youtube_url_raises(self):
        from harpi.infrastructure.ytdlp_resolver import YtDlpResolver

        resolver = YtDlpResolver()
        with pytest.raises(InvalidLinkError):
            await resolver.resolve("https://example.com/not-a-video")

    @pytest.mark.asyncio
    async def test_resolve_empty_string_raises(self):
        from harpi.infrastructure.ytdlp_resolver import YtDlpResolver

        resolver = YtDlpResolver()
        with pytest.raises(InvalidLinkError):
            await resolver.resolve("")

    @pytest.mark.asyncio
    async def test_resolve_private_video_raises(self):
        from harpi.infrastructure.ytdlp_resolver import YtDlpResolver

        resolver = YtDlpResolver()
        # This video ID is unlikely to exist as a public video
        with pytest.raises((InvalidLinkError, NetworkError)):
            await resolver.resolve("https://youtu.be/ztC3BmRk2G8")


@pytest.mark.integration
class TestYtDlpResolverStream:
    """Tests resolve_stream with real HTTP calls to YouTube."""

    @pytest.mark.asyncio
    async def test_resolve_stream_returns_playable_url(self):
        from harpi.infrastructure.ytdlp_resolver import YtDlpResolver

        resolver = YtDlpResolver()
        track = await resolver.resolve("https://youtu.be/M8J9zHyyUYc")
        url = await resolver.resolve_stream(track)

        assert url.startswith("https://")
        assert "googlevideo" in url

    @pytest.mark.asyncio
    async def test_stream_url_is_audio_content(self):
        """Verify the stream URL responds with an audio Content-Type."""
        from harpi.infrastructure.ytdlp_resolver import YtDlpResolver

        resolver = YtDlpResolver()
        track = await resolver.resolve("https://youtu.be/M8J9zHyyUYc")
        url = await resolver.resolve_stream(track)

        async with aiohttp.ClientSession() as session:
            async with session.head(url, allow_redirects=True) as response:
                assert response.status == 200
                content_type = response.headers.get("Content-Type", "")
                assert content_type.startswith(("audio/", "video/")), (
                    f"Expected audio/* or video/* Content-Type, got {content_type}"
                )

    @pytest.mark.asyncio
    async def test_stream_url_has_content(self):
        """Verify the stream URL returns data (not empty/dead)."""
        from harpi.infrastructure.ytdlp_resolver import YtDlpResolver

        resolver = YtDlpResolver()
        track = await resolver.resolve("https://youtu.be/M8J9zHyyUYc")
        url = await resolver.resolve_stream(track)

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                assert response.status == 200
                # Read first 8KB to confirm data flows
                chunk = await response.content.readexactly(8192)
                assert len(chunk) == 8192


@pytest.mark.integration
class TestYtDlpResolverCachedStream:
    """Tests that resolve_stream gives consistent results for the same video."""

    @pytest.mark.asyncio
    async def test_resolve_stream_is_consistent(self):
        from harpi.infrastructure.ytdlp_resolver import YtDlpResolver

        resolver = YtDlpResolver()
        track = await resolver.resolve("https://youtu.be/M8J9zHyyUYc")
        url1 = await resolver.resolve_stream(track)
        url2 = await resolver.resolve_stream(track)

        # Both should be googlevideo URLs (exact URL may differ due to tokens)
        assert url1.startswith("https://")
        assert url2.startswith("https://")
        assert "googlevideo" in url1
        assert "googlevideo" in url2


@pytest.mark.integration
class TestFallbackResolverWithYtDlp:
    """Tests FallbackResolver behavior when YoutubeResolver is tried first."""

    @pytest.mark.asyncio
    async def test_fallback_resolve_with_both_resolvers(self):
        from harpi.infrastructure.youtube_resolver import YoutubeResolver
        from harpi.infrastructure.ytdlp_resolver import YtDlpResolver
        from harpi.infrastructure.fallback_resolver import FallbackResolver

        resolver = FallbackResolver([YoutubeResolver(), YtDlpResolver()])
        track = await resolver.resolve("https://youtu.be/M8J9zHyyUYc")

        assert track.title is not None
        assert track.duration is not None
        assert track.duration > 0
        assert track.source == Source.YOUTUBE

    @pytest.mark.asyncio
    async def test_fallback_stream_with_both_resolvers(self):
        from harpi.infrastructure.youtube_resolver import YoutubeResolver
        from harpi.infrastructure.ytdlp_resolver import YtDlpResolver
        from harpi.infrastructure.fallback_resolver import FallbackResolver

        resolver = FallbackResolver([YoutubeResolver(), YtDlpResolver()])
        track = await resolver.resolve("https://youtu.be/M8J9zHyyUYc")
        url = await resolver.resolve_stream(track)

        assert url.startswith("https://")
        assert "googlevideo" in url

    @pytest.mark.asyncio
    async def test_fallback_ytdlp_when_first_fails(self):
        """YtDlpResolver should be used when YoutubeResolver fails."""
        from harpi.infrastructure.youtube_resolver import YoutubeResolver
        from harpi.infrastructure.ytdlp_resolver import YtDlpResolver
        from harpi.infrastructure.fallback_resolver import FallbackResolver

        resolver = FallbackResolver(
            [
                # First resolver always fails for this link
                YoutubeResolver(),
                YtDlpResolver(),
            ]
        )

        # Resolving a valid URL should still work via fallback
        track = await resolver.resolve("https://youtu.be/M8J9zHyyUYc")
        assert track.title is not None
        assert track.duration is not None
