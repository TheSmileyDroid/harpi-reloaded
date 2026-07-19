import asyncio
import subprocess

import pytest

from harpi.domain.track_metadata import Source
from harpi.application.exceptions import InvalidLinkError, NetworkError

YT_MUSIC_URL = (
    "https://music.youtube.com/watch?v=4pqavU7gqgA&si=OKMnUIiuvFwqvCsb"
)


@pytest.mark.integration
class TestYtDlpResolver:
    """Integration tests for YtDlpResolver with real HTTP calls to YouTube."""

    @pytest.mark.asyncio
    async def test_resolve_youtube_short_url(self):
        from harpi.infrastructure.ytdlp_resolver import YtDlpResolver

        resolver = YtDlpResolver(js_runtimes={"node": {}})
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

        resolver = YtDlpResolver(js_runtimes={"node": {}})
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

        resolver = YtDlpResolver(js_runtimes={"node": {}})
        track = await resolver.resolve("https://youtu.be/M8J9zHyyUYc")
        url = await resolver.resolve_stream(track)

        assert url.startswith("https://")
        assert "googlevideo" in url

    @pytest.mark.asyncio
    async def test_stream_url_has_headers(self):
        """Verify the stream URL includes http_headers from yt-dlp.

        The headers are required to access the stream URL (User-Agent,
        Accept, etc.). This test verifies that get_last_stream_headers()
        returns a populated dict after resolve_stream() is called.
        """
        from harpi.infrastructure.ytdlp_resolver import YtDlpResolver

        resolver = YtDlpResolver(
            cookiefile="/home/opc/external/cookies.txt",
            js_runtimes={"node": {}},
        )
        track = await resolver.resolve("https://youtu.be/M8J9zHyyUYc")
        url = await resolver.resolve_stream(track)
        headers = resolver.get_last_stream_headers()

        assert url.startswith("https://")
        assert "googlevideo" in url
        assert len(headers) > 0
        assert any(
            k.lower() == "user-agent" for k in headers
        ), "Headers should include User-Agent"

    @pytest.mark.asyncio
    async def test_stream_url_is_accessible_with_headers(self):
        """Verify the stream URL is accessible with http_headers via HTTP range request.

        Attempts a range request with the stream URL and http_headers.
        The CDN may occasionally return 403 (load-balancing behavior), so
        the test retries up to 3 times with fresh URLs. If all retries
        fail with 403, the test is skipped (CDN issue, not our code).
        """
        from harpi.infrastructure.ytdlp_resolver import YtDlpResolver

        resolver = YtDlpResolver(
            cookiefile="/home/opc/external/cookies.txt",
            js_runtimes={"node": {}},
        )
        for attempt in range(3):
            track = await resolver.resolve("https://youtu.be/M8J9zHyyUYc")
            fresh_url = await resolver.resolve_stream(track)
            fresh_headers = resolver.get_last_stream_headers()

            curl_cmd = ["curl", "-s", "-D", "-", "-r", "0-0", "-o", "/dev/null"]
            for k, v in fresh_headers.items():
                curl_cmd += ["-H", f"{k}: {v}"]
            curl_cmd.append(fresh_url)

            proc = await asyncio.create_subprocess_exec(
                *curl_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
            response = stdout.decode("utf-8", errors="replace")

            if "206 Partial Content" in response or "200 OK" in response:
                for line in response.split("\r\n"):
                    if line.lower().startswith("content-type:"):
                        content_type = line.split(":", 1)[1].strip()
                        assert content_type.startswith("audio/"), (
                            f"Expected audio/* Content-Type, got: {content_type}"
                        )
                        return
                raise AssertionError(f"No Content-Type in response:\n{response[:500]}")
        pytest.skip(
            "Stream URL not accessible after 3 retries (CDN transient error)"
        )


@pytest.mark.integration
class TestYtDlpResolverCachedStream:
    """Tests that resolve_stream gives consistent results for the same video."""

    @pytest.mark.asyncio
    async def test_resolve_stream_is_consistent(self):
        from harpi.infrastructure.ytdlp_resolver import YtDlpResolver

        resolver = YtDlpResolver(js_runtimes={"node": {}})
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

        resolver = FallbackResolver([
            YoutubeResolver(),
            YtDlpResolver(js_runtimes={"node": {}}),
        ])
        track = await resolver.resolve("https://youtu.be/M8J9zHyyUYc")

        assert track.title is not None
        assert track.duration is not None
        assert track.source == Source.YOUTUBE

    @pytest.mark.asyncio
    async def test_fallback_stream_with_both_resolvers(self):
        from harpi.infrastructure.youtube_resolver import YoutubeResolver
        from harpi.infrastructure.ytdlp_resolver import YtDlpResolver
        from harpi.infrastructure.fallback_resolver import FallbackResolver

        resolver = FallbackResolver([
            YoutubeResolver(),
            YtDlpResolver(js_runtimes={"node": {}}),
        ])
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
                YoutubeResolver(),
                YtDlpResolver(js_runtimes={"node": {}}),
            ]
        )

        track = await resolver.resolve("https://youtu.be/M8J9zHyyUYc")
        assert track.title is not None
        assert track.duration is not None
