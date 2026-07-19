"""E2E test for the full audio pipeline: resolve → yt-dlp pipe → ffmpeg → PCM.

This test exercises the real YouTube resolvers and the yt-dlp→ffmpeg pipeline
to verify that the entire pipeline produces valid PCM audio data for Discord
playback. It does NOT require a Discord token — it tests the pipeline up to
the point where audio bytes are produced.
"""

import subprocess

import numpy as np
import pytest

from harpi.application.exceptions import InvalidLinkError
from harpi.domain.track_metadata import Source

pytestmark = pytest.mark.e2e

YT_MUSIC_URL = (
    "https://music.youtube.com/watch?v=4pqavU7gqgA&si=OKMnUIiuvFwqvCsb"
)
REGULAR_YT_URL = "https://youtu.be/M8J9zHyyUYc"
COOKIEFILE = "/home/opc/external/cookies.txt"
PCM_FRAME_SIZE = 960  # Encoder.FRAME_SIZE = 20ms at 48kHz
_FFMPEG_PCM_ARGS = ["-f", "s16le", "-ar", "48000", "-ac", "2", "pipe:1"]


def _spawn_ytdlp_pipeline(url: str) -> tuple[int, bytes]:
    """Spawn yt-dlp piped to ffmpeg (mirrors DiscordPlayer._spawn_ytdlp_pipeline)."""
    ytdlp_proc = subprocess.Popen(
        [
            "yt-dlp",
            "--cookies", COOKIEFILE,
            "--js-runtimes", "node",
            "-f", "m4a/bestaudio/best",
            "-o", "-",
            url,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    ffmpeg_proc = subprocess.Popen(
        ["ffmpeg", "-i", "pipe:0", *["-t", "3"], *_FFMPEG_PCM_ARGS],
        stdin=ytdlp_proc.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if ytdlp_proc.stdout:
        ytdlp_proc.stdout.close()
    stdout, _ = ffmpeg_proc.communicate(timeout=60)
    return ffmpeg_proc.returncode, stdout


@pytest.mark.asyncio
class TestAudioPipelineE2E:
    """E2E test for the full audio pipeline without Discord."""

    async def test_ytdlp_pipeline_produces_pcm(self):
        """YtDlpResolver + yt-dlp pipe produces playable PCM audio from a regular
        YouTube URL."""
        from harpi.infrastructure.ytdlp_resolver import YtDlpResolver

        resolver = YtDlpResolver(
            cookiefile=COOKIEFILE,
            js_runtimes={"node": {}},
        )
        track = await resolver.resolve(REGULAR_YT_URL)
        assert track.title is not None
        assert len(track.title) > 0
        assert track.duration is not None
        assert track.duration > 0
        assert track.source == Source.YOUTUBE

        assert resolver.get_cookiefile() == COOKIEFILE

        rc, pcm_data = _spawn_ytdlp_pipeline(track.link)
        assert rc == 0, f"Pipeline ffmpeg exited with {rc}"
        assert len(pcm_data) >= PCM_FRAME_SIZE, (
            f"Expected at least {PCM_FRAME_SIZE} bytes of PCM, got {len(pcm_data)}"
        )
        samples = np.frombuffer(pcm_data, dtype=np.int16)
        assert np.max(np.abs(samples)) > 0, "PCM data is all zeros (silence)"

    async def test_ytdlp_pipeline_youtube_music_produces_pcm(self):
        """YtDlpResolver + yt-dlp pipe produces PCM from a YouTube Music URL."""
        from harpi.infrastructure.ytdlp_resolver import YtDlpResolver

        resolver = YtDlpResolver(
            cookiefile=COOKIEFILE,
            js_runtimes={"node": {}},
        )
        track = await resolver.resolve(YT_MUSIC_URL)
        assert track.title is not None
        assert len(track.title) > 0
        assert track.duration is not None
        assert track.duration > 0
        assert track.source == Source.YOUTUBE
        assert track.source_id == "4pqavU7gqgA"

        rc, pcm_data = _spawn_ytdlp_pipeline(track.link)
        assert rc == 0, f"Pipeline ffmpeg exited with {rc}"
        assert len(pcm_data) >= PCM_FRAME_SIZE, (
            f"Expected at least {PCM_FRAME_SIZE} bytes of PCM, got {len(pcm_data)}"
        )
        samples = np.frombuffer(pcm_data, dtype=np.int16)
        assert np.max(np.abs(samples)) > 0, "PCM data is all zeros (silence)"

    async def test_fallback_resolver_pipeline_produces_pcm(self):
        """FallbackResolver + yt-dlp pipe produces PCM (exercises delegate
        get_cookiefile)."""
        from harpi.infrastructure.youtube_resolver import YoutubeResolver
        from harpi.infrastructure.ytdlp_resolver import YtDlpResolver
        from harpi.infrastructure.fallback_resolver import FallbackResolver

        resolver = FallbackResolver([
            YoutubeResolver(),
            YtDlpResolver(
                cookiefile=COOKIEFILE,
                js_runtimes={"node": {}},
            ),
        ])
        track = await resolver.resolve(YT_MUSIC_URL)
        assert track.title is not None
        assert track.duration is not None

        assert resolver.get_cookiefile() == COOKIEFILE

        rc, pcm_data = _spawn_ytdlp_pipeline(track.link)
        assert rc == 0, f"Pipeline ffmpeg exited with {rc}"
        assert len(pcm_data) >= PCM_FRAME_SIZE, (
            f"Expected at least {PCM_FRAME_SIZE} bytes of PCM, got {len(pcm_data)}"
        )
        samples = np.frombuffer(pcm_data, dtype=np.int16)
        assert np.max(np.abs(samples)) > 0, "PCM data is all zeros (silence)"

    async def test_resolve_invalid_url_raises(self):
        """Invalid URLs raise InvalidLinkError."""
        from harpi.infrastructure.ytdlp_resolver import YtDlpResolver

        resolver = YtDlpResolver(js_runtimes={"node": {}})
        with pytest.raises(InvalidLinkError):
            await resolver.resolve("https://youtu.be/ID_INVALIDO_12345")
