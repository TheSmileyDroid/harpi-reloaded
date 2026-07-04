from typing import Any
import pytest
from harpi.application.ports.audio import AudioPlayerProtocol
from harpi.domain.track_metadata import TrackMetadata, Source


class FakeAudioSource:
    def cleanup(self) -> None:
        pass


class FakeVoiceClient:
    def __init__(self):
        self._is_playing = False
        self._is_paused = False
        self._source = None
        self._after = None
        self.play_calls = 0

    def play(self, source, after=None):
        self._source = source
        self._after = after
        self._is_playing = True
        self._is_paused = False
        self.play_calls += 1

    def pause(self):
        self._is_paused = True
        self._is_playing = False

    def resume(self):
        self._is_paused = False
        self._is_playing = True

    def stop(self):
        self._is_playing = False
        self._is_paused = False
        if self._after is not None:
            after = self._after
            self._after = None
            after(None)

    def is_playing(self):
        return self._is_playing

    def is_paused(self):
        return self._is_paused


@pytest.fixture
def voice_client():
    return FakeVoiceClient()


@pytest.fixture
def player(voice_client):
    from harpi.infrastructure.discord_player import DiscordPlayer

    class TestDiscordPlayer(DiscordPlayer):
        async def _build_mixed_source(self, track: TrackMetadata) -> Any:
            return FakeAudioSource()

    return TestDiscordPlayer(voice_client=voice_client)


@pytest.fixture
def track():
    return TrackMetadata(
        link="https://youtu.be/abc123",
        title="Test Track",
        duration=120,
        source=Source.YOUTUBE,
    )


@pytest.fixture
def bg_track():
    return TrackMetadata(
        link="https://youtu.be/bg123",
        title="BG Track",
        duration=300,
        source=Source.YOUTUBE,
    )


class TestDiscordPlayerInitialState:
    async def test_playing_is_none_initially(self, player: AudioPlayerProtocol):
        assert player.playing is None

    async def test_is_paused_is_false_initially(self, player: AudioPlayerProtocol):
        assert player.is_paused is False

    async def test_is_stopped_is_false_initially(self, player: AudioPlayerProtocol):
        assert player.is_stopped is False

    async def test_background_tracks_is_empty_list(self, player: AudioPlayerProtocol):
        assert player.background_tracks == []


class TestDiscordPlayerPlay:
    async def test_play_sets_playing_to_track(
        self, player: AudioPlayerProtocol, track: TrackMetadata
    ):
        await player.play(track)
        assert player.playing is track

    async def test_play_calls_voice_client_play(
        self,
        player: AudioPlayerProtocol,
        track: TrackMetadata,
        voice_client: FakeVoiceClient,
    ):
        await player.play(track)
        assert voice_client.is_playing()

    async def test_play_clears_is_stopped(
        self, player: AudioPlayerProtocol, track: TrackMetadata
    ):
        await player.stop()
        await player.play(track)
        assert player.is_stopped is False

    async def test_play_clears_is_paused(
        self, player: AudioPlayerProtocol, track: TrackMetadata
    ):
        await player.pause()
        await player.play(track)
        assert player.is_paused is False

    async def test_play_passes_source_to_voice_client(
        self,
        player: AudioPlayerProtocol,
        track: TrackMetadata,
        voice_client: FakeVoiceClient,
    ):
        await player.play(track)
        assert voice_client._source is not None


class TestDiscordPlayerPause:
    async def test_pause_sets_is_paused(
        self, player: AudioPlayerProtocol, track: TrackMetadata
    ):
        await player.play(track)
        await player.pause()
        assert player.is_paused is True

    async def test_pause_calls_voice_client_pause(
        self,
        player: AudioPlayerProtocol,
        track: TrackMetadata,
        voice_client: FakeVoiceClient,
    ):
        await player.play(track)
        await player.pause()
        assert voice_client.is_paused()


class TestDiscordPlayerResume:
    async def test_resume_clears_is_paused(
        self, player: AudioPlayerProtocol, track: TrackMetadata
    ):
        await player.play(track)
        await player.pause()
        await player.resume()
        assert player.is_paused is False

    async def test_resume_calls_voice_client_resume(
        self,
        player: AudioPlayerProtocol,
        track: TrackMetadata,
        voice_client: FakeVoiceClient,
    ):
        await player.play(track)
        await player.pause()
        await player.resume()
        assert not voice_client.is_paused()


class TestDiscordPlayerStop:
    async def test_stop_sets_is_stopped(
        self, player: AudioPlayerProtocol, track: TrackMetadata
    ):
        await player.play(track)
        await player.stop()
        assert player.is_stopped is True

    async def test_stop_clears_playing(
        self, player: AudioPlayerProtocol, track: TrackMetadata
    ):
        await player.play(track)
        await player.stop()
        assert player.playing is None

    async def test_stop_calls_voice_client_stop(
        self,
        player: AudioPlayerProtocol,
        track: TrackMetadata,
        voice_client: FakeVoiceClient,
    ):
        await player.play(track)
        await player.stop()
        assert not voice_client.is_playing()
        assert not voice_client.is_paused()


class TestDiscordPlayerErrors:
    async def test_play_without_voice_client_raises(self, track: TrackMetadata):
        from harpi.infrastructure.discord_player import DiscordPlayer

        player = DiscordPlayer()

        with pytest.raises(RuntimeError, match="Not connected"):
            await player.play(track)

    async def test_play_raises_when_build_mixed_source_fails(
        self, voice_client, track: TrackMetadata
    ):
        from harpi.infrastructure.discord_player import DiscordPlayer

        class FailingDiscordPlayer(DiscordPlayer):
            async def _build_mixed_source(self, track: TrackMetadata) -> Any:
                raise ValueError("No audio stream available")

        player = FailingDiscordPlayer(voice_client=voice_client)

        with pytest.raises(ValueError, match="No audio stream available"):
            await player.play(track)

    async def test_pause_without_voice_client_raises(self, track: TrackMetadata):
        from harpi.infrastructure.discord_player import DiscordPlayer

        player = DiscordPlayer()

        with pytest.raises(RuntimeError, match="Not connected"):
            await player.pause()

    async def test_resume_without_voice_client_raises(self, track: TrackMetadata):
        from harpi.infrastructure.discord_player import DiscordPlayer

        player = DiscordPlayer()

        with pytest.raises(RuntimeError, match="Not connected"):
            await player.resume()

    async def test_stop_without_voice_client_raises(self, track: TrackMetadata):
        from harpi.infrastructure.discord_player import DiscordPlayer

        player = DiscordPlayer()

        with pytest.raises(RuntimeError, match="Not connected"):
            await player.stop()


class TestDiscordPlayerBackgroundSource:
    async def test_add_background_source_adds_to_list(
        self, player, bg_track: TrackMetadata
    ):
        await player.add_background_source(bg_track)
        assert len(player.background_tracks) == 1
        assert player.background_tracks[0] is bg_track

    async def test_add_background_source_multiple(
        self, player, bg_track: TrackMetadata
    ):
        await player.add_background_source(bg_track)
        await player.add_background_source(bg_track)
        assert len(player.background_tracks) == 2

    async def test_remove_background_source_removes_from_tracks(
        self, player, bg_track: TrackMetadata
    ):
        player.background_tracks = [bg_track]
        player.remove_background_source(0)
        assert len(player.background_tracks) == 0

    async def test_remove_background_source_out_of_bounds_raises(self, player):
        with pytest.raises(IndexError):
            player.remove_background_source(5)

    async def test_add_background_source_before_play_starts(
        self, player, bg_track: TrackMetadata, track: TrackMetadata
    ):
        await player.add_background_source(bg_track)
        assert len(player.background_tracks) == 1
        await player.play(track)
        assert player.playing is track


class TestDiscordPlayerStopNoCrash:
    async def test_stop_without_playing_does_not_crash(self, player):
        await player.stop()


class FakeStreamProcess:
    """Processo fake cujo stdout entrega N frames PCM de amplitude constante."""

    def __init__(self, frames: int, value: int = 0):
        import io

        import numpy as np
        from harpi.infrastructure.mixed_audio_source import PCM_FRAME_SIZE

        frame = np.full(PCM_FRAME_SIZE // 2, value, dtype=np.int16).tobytes()
        self.stdout = io.BytesIO(frame * frames)
        self.killed = False

    def kill(self):
        self.killed = True

    def wait(self, timeout: float = 1):
        pass


def _first_sample(pcm: bytes) -> int:
    import numpy as np

    return int(np.frombuffer(pcm, dtype=np.int16)[0])


@pytest.fixture
def make_streamed_player(voice_client):
    from harpi.infrastructure.discord_player import DiscordPlayer

    def _make(procs: list[FakeStreamProcess]):
        class StreamedDiscordPlayer(DiscordPlayer):
            async def _spawn_source_process(self, track: TrackMetadata) -> Any:
                return procs.pop(0)

        return StreamedDiscordPlayer(voice_client=voice_client)

    return _make


class TestDiscordPlayerLiveVolume:
    async def test_set_volume_mid_playback_changes_output(
        self, make_streamed_player, voice_client, track
    ):
        player = make_streamed_player([FakeStreamProcess(3, value=1000)])
        await player.play(track)

        player.set_volume(0.5)

        assert _first_sample(voice_client._source.read()) == 500

    async def test_set_background_volume_mid_playback_changes_output(
        self, make_streamed_player, voice_client, track, bg_track
    ):
        player = make_streamed_player(
            [FakeStreamProcess(3, value=0), FakeStreamProcess(3, value=1000)]
        )
        await player.play(track)
        await player.add_background_source(bg_track)

        player.set_background_volume(0.2)

        assert _first_sample(voice_client._source.read()) == 200

    async def test_duck_mid_playback_lowers_background_now(
        self, make_streamed_player, voice_client, track, bg_track
    ):
        player = make_streamed_player(
            [FakeStreamProcess(4, value=0), FakeStreamProcess(4, value=1000)]
        )
        await player.play(track)
        await player.add_background_source(bg_track)
        player.set_ducking(0.1)

        await player.duck()
        assert _first_sample(voice_client._source.read()) == 100

        await player.unduck()
        assert _first_sample(voice_client._source.read()) == 100 * 5


class TestDiscordPlayerBackgroundRemovalMapping:
    async def test_remove_background_keeps_foreground_playing(
        self, make_streamed_player, voice_client, track, bg_track
    ):
        fg_proc = FakeStreamProcess(3, value=1000)
        bg_proc = FakeStreamProcess(3, value=200)
        player = make_streamed_player([fg_proc, bg_proc])
        await player.play(track)
        await player.add_background_source(bg_track)

        player.remove_background_source(0)

        assert bg_proc.killed is True
        assert fg_proc.killed is False
        assert _first_sample(voice_client._source.read()) == 1000


class TestDiscordPlayerTrackEnd:
    async def test_foreground_end_fires_on_finish_with_background_active(
        self, make_streamed_player, voice_client, track, bg_track
    ):
        import asyncio

        player = make_streamed_player(
            [FakeStreamProcess(1, value=1000), FakeStreamProcess(5, value=100)]
        )
        finished = asyncio.Event()

        async def on_finish():
            finished.set()

        await player.play(track, on_finish=on_finish)
        await player.add_background_source(bg_track)

        voice_client._source.read()
        voice_client._source.read()
        await asyncio.wait_for(finished.wait(), timeout=1)

        assert player.playing is None

    async def test_play_after_foreground_end_swaps_without_restarting_voice(
        self, make_streamed_player, voice_client, track, bg_track
    ):
        import asyncio

        track2 = TrackMetadata(
            link="https://youtu.be/next",
            title="Next Track",
            duration=90,
            source=Source.YOUTUBE,
        )
        player = make_streamed_player(
            [
                FakeStreamProcess(1, value=1000),
                FakeStreamProcess(9, value=0),
                FakeStreamProcess(3, value=800),
            ]
        )
        finished = asyncio.Event()

        async def on_finish():
            finished.set()

        await player.play(track, on_finish=on_finish)
        await player.add_background_source(bg_track)
        voice_client._source.read()
        voice_client._source.read()
        await asyncio.wait_for(finished.wait(), timeout=1)

        await player.play(track2)

        assert voice_client.play_calls == 1
        assert player.playing is track2
        assert _first_sample(voice_client._source.read()) == 800

    async def test_all_sources_ending_fires_on_finish_via_after(
        self, make_streamed_player, voice_client, track
    ):
        import asyncio

        player = make_streamed_player([FakeStreamProcess(1, value=1000)])
        finished = asyncio.Event()

        async def on_finish():
            finished.set()

        await player.play(track, on_finish=on_finish)

        assert voice_client._source.read() != b""
        assert voice_client._source.read() == b""
        after = voice_client._after
        assert after is not None
        after(None)
        await asyncio.wait_for(finished.wait(), timeout=1)

    async def test_stop_does_not_fire_on_finish(
        self, make_streamed_player, voice_client, track
    ):
        import asyncio

        player = make_streamed_player([FakeStreamProcess(3, value=1000)])
        calls: list[int] = []

        async def on_finish():
            calls.append(1)

        await player.play(track, on_finish=on_finish)
        await player.stop()
        await asyncio.sleep(0.05)

        assert calls == []
