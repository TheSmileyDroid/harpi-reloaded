from test.unit.conftest import FakeResolver, FakeVoiceClient, DeferredAfterVoiceClient
from typing import Any
import pytest
from harpi.application.ports.audio import (
    AudioPlayerProtocol,
    AudioResolverProtocol,
)
from harpi.domain.track_metadata import TrackMetadata, Source


class FakeAudioSource:
    def cleanup(self) -> None:
        pass


@pytest.fixture
def voice_client():
    return FakeVoiceClient()


@pytest.fixture
def player(voice_client):
    from harpi.infrastructure.discord_player import DiscordPlayer

    class TestDiscordPlayer(DiscordPlayer):
        async def _build_mixed_source(self, track: TrackMetadata) -> Any:
            return FakeAudioSource()

    return TestDiscordPlayer(voice_client=voice_client, resolver=FakeResolver())


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

        player = DiscordPlayer(resolver=FakeResolver())

        with pytest.raises(RuntimeError, match="Not connected"):
            await player.play(track)

    async def test_play_raises_when_build_mixed_source_fails(
        self, voice_client, track: TrackMetadata
    ):
        from harpi.infrastructure.discord_player import DiscordPlayer

        class FailingDiscordPlayer(DiscordPlayer):
            async def _build_mixed_source(self, track: TrackMetadata) -> Any:
                raise ValueError("No audio stream available")

        player = FailingDiscordPlayer(
            voice_client=voice_client, resolver=FakeResolver()
        )

        with pytest.raises(ValueError, match="No audio stream available"):
            await player.play(track)

    async def test_pause_without_voice_client_raises(self, track: TrackMetadata):
        from harpi.infrastructure.discord_player import DiscordPlayer

        player = DiscordPlayer(resolver=FakeResolver())

        with pytest.raises(RuntimeError, match="Not connected"):
            await player.pause()

    async def test_resume_without_voice_client_raises(self, track: TrackMetadata):
        from harpi.infrastructure.discord_player import DiscordPlayer

        player = DiscordPlayer(resolver=FakeResolver())

        with pytest.raises(RuntimeError, match="Not connected"):
            await player.resume()

    async def test_stop_without_voice_client_raises(self, track: TrackMetadata):
        from harpi.infrastructure.discord_player import DiscordPlayer

        player = DiscordPlayer(resolver=FakeResolver())

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
            async def _spawn_source_process(
                self, track: TrackMetadata, loop: bool = False
            ) -> Any:
                return procs.pop(0)

        return StreamedDiscordPlayer(voice_client=voice_client, resolver=FakeResolver())

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
            [
                FakeStreamProcess(3, value=0),
                FakeStreamProcess(3, value=1000),
            ]
        )
        await player.play(track)
        await player.add_background_source(bg_track)

        player.set_background_volume(0.2)

        assert _first_sample(voice_client._source.read()) == 200


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
            [
                FakeStreamProcess(1, value=1000),
                FakeStreamProcess(5, value=100),
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


class TestDiscordPlayerStaleCallback:
    """Tests that stale `_on_finish` callbacks (from a previous playback session)
    are ignored via the generation counter."""

    async def test_stale_after_callback_is_ignored(self, track):
        from harpi.infrastructure.discord_player import DiscordPlayer

        vc = DeferredAfterVoiceClient()

        class TestPlayer(DiscordPlayer):
            async def _build_mixed_source(self, track):
                return FakeAudioSource()

        player = TestPlayer(voice_client=vc, resolver=FakeResolver())
        finish_calls: list[int] = []

        async def on_finish():
            finish_calls.append(1)

        # Play track A (generation becomes 1)
        await player.play(track, on_finish=on_finish)
        assert vc.is_playing()

        # Stop: generation becomes 2, after is stored (not fired)
        await player.stop()
        assert not vc.is_playing()

        # Play track B (generation becomes 3)
        track_b = TrackMetadata(
            link="https://youtu.be/bbb",
            title="Track B",
            duration=60,
            source=Source.YOUTUBE,
        )
        await player.play(track_b, on_finish=on_finish)

        # Fire the stale `after` from the stop() call (old generation)
        vc.fire_stored_after()

        # The stale callback should NOT have triggered on_track_end
        assert finish_calls == []

    async def test_current_after_callback_schedules(self, track):
        from harpi.infrastructure.discord_player import DiscordPlayer
        import asyncio

        vc = DeferredAfterVoiceClient()

        class TestPlayer(DiscordPlayer):
            async def _build_mixed_source(self, track):
                return FakeAudioSource()

        player = TestPlayer(voice_client=vc, resolver=FakeResolver())
        finished = asyncio.Event()

        async def on_finish():
            finished.set()

        await player.play(track, on_finish=on_finish)

        # Fire the current `after` callback directly (correct generation)
        after = vc._after
        assert after is not None
        after(None)
        await asyncio.wait_for(finished.wait(), timeout=1)

    async def test_generation_increments_on_stop(self, track):
        from harpi.infrastructure.discord_player import DiscordPlayer

        vc = DeferredAfterVoiceClient()

        class TestPlayer(DiscordPlayer):
            async def _build_mixed_source(self, track):
                return FakeAudioSource()

        player = TestPlayer(voice_client=vc, resolver=FakeResolver())
        initial_gen = player._play_generation

        await player.play(track)
        assert player._play_generation == initial_gen + 1

        await player.stop()
        assert player._play_generation == initial_gen + 2


class TestDiscordPlayerBackgroundLooping:
    async def test_background_added_mid_playback_spawns_with_looping(
        self, voice_client, track, bg_track
    ):
        from harpi.infrastructure.discord_player import DiscordPlayer

        spawned: list[tuple[str, bool]] = []

        class RecordingPlayer(DiscordPlayer):
            async def _spawn_source_process(
                self, track: TrackMetadata, loop: bool = False
            ) -> Any:
                spawned.append((track.link, loop))
                return FakeStreamProcess(3, value=0)

        player = RecordingPlayer(voice_client=voice_client, resolver=FakeResolver())
        await player.play(track)
        await player.add_background_source(bg_track)

        assert spawned == [(track.link, False), (bg_track.link, True)]

    async def test_background_present_before_play_spawns_with_looping(
        self, voice_client, track, bg_track
    ):
        from harpi.infrastructure.discord_player import DiscordPlayer

        spawned: list[tuple[str, bool]] = []

        class RecordingPlayer(DiscordPlayer):
            async def _spawn_source_process(
                self, track: TrackMetadata, loop: bool = False
            ) -> Any:
                spawned.append((track.link, loop))
                return FakeStreamProcess(3, value=0)

        player = RecordingPlayer(voice_client=voice_client, resolver=FakeResolver())
        await player.add_background_source(bg_track)
        await player.play(track)

        assert spawned == [(track.link, False), (bg_track.link, True)]

    def test_spawn_pcm_process_adds_stream_loop_flag(self):
        from harpi.infrastructure.discord_player import DiscordPlayer

        recorded: list[list[str]] = []

        class RecordingPopenPlayer(DiscordPlayer):
            @staticmethod
            def _popen(args: list[str], **kwargs) -> Any:
                recorded.append(args)

        player = RecordingPopenPlayer(resolver=FakeResolver())
        player._spawn_pcm_process("http://x", loop=True)
        player._spawn_pcm_process("http://x", loop=False)

        looped, plain = recorded
        assert "-stream_loop" in looped
        assert looped.index("-stream_loop") < looped.index("-i")
        assert "-stream_loop" not in plain


class TestDiscordPlayerUsesResolver:
    async def test_play_resolves_stream_url_via_injected_resolver(
        self, voice_client, track
    ):
        from harpi.infrastructure.discord_player import DiscordPlayer

        class StubResolver(AudioResolverProtocol):
            async def resolve(self, link: str) -> TrackMetadata:
                raise AssertionError("play must not call resolve()")

            async def resolve_stream(self, track: TrackMetadata) -> str:
                return f"http://stream/{track.link}"

        captured: list[str] = []

        class CapturingPlayer(DiscordPlayer):
            def _spawn_pcm_process(
                self,
                url: str,
                loop: bool = False,
                headers: dict | None = None,
                cookies: dict | None = None,
            ) -> Any:
                captured.append(url)
                return FakeStreamProcess(3, value=0)

        player = CapturingPlayer(voice_client=voice_client, resolver=StubResolver())
        await player.play(track)

        assert captured == [f"http://stream/{track.link}"]

    async def test_background_resolved_via_injected_resolver(
        self, voice_client, track, bg_track
    ):
        from harpi.infrastructure.discord_player import DiscordPlayer

        class StubResolver(AudioResolverProtocol):
            async def resolve(self, link: str) -> TrackMetadata:
                raise AssertionError("play must not call resolve()")

            async def resolve_stream(self, track: TrackMetadata) -> str:
                return f"http://stream/{track.link}"

        captured: list[str] = []

        class CapturingPlayer(DiscordPlayer):
            def _spawn_pcm_process(
                self,
                url: str,
                loop: bool = False,
                headers: dict | None = None,
                cookies: dict | None = None,
            ) -> Any:
                captured.append(url)
                return FakeStreamProcess(3, value=0)

        player = CapturingPlayer(voice_client=voice_client, resolver=StubResolver())
        await player.play(track)
        await player.add_background_source(bg_track)

        assert f"http://stream/{bg_track.link}" in captured


class TestDiscordPlayerPosition:
    async def test_position_when_paused(self, player, track):
        await player.play(track)
        await player.pause()
        pos = player.position
        assert pos is not None
        assert isinstance(pos, float)

    async def test_position_when_start_time_none(self):
        from harpi.infrastructure.discord_player import DiscordPlayer

        player = DiscordPlayer(voice_client=FakeVoiceClient(), resolver=FakeResolver())
        player._current = TrackMetadata(
            link="https://youtu.be/abc",
            title="Test",
            duration=120,
            source=Source.YOUTUBE,
        )
        player._start_time = None
        assert player.position is None


class TestDiscordPlayerStopCleanup:
    async def test_stop_with_mixed_source_cleans_up(
        self, make_streamed_player, voice_client, track
    ):
        player = make_streamed_player([FakeStreamProcess(3, value=0)])
        await player.play(track)
        assert player._mixed_source is not None

        await player.stop()

        assert player._mixed_source is None
        assert player._fg_proc is None


class TestDiscordPlayerOnFinish:
    async def test_on_finish_no_error(self, make_streamed_player, voice_client, track):
        import asyncio

        player = make_streamed_player([FakeStreamProcess(1, value=1000)])
        finished = asyncio.Event()

        async def on_finish():
            finished.set()

        await player.play(track, on_finish=on_finish)

        after = voice_client._after
        assert after is not None
        after(None)
        await asyncio.wait_for(finished.wait(), timeout=1)


class TestDiscordPlayerSetDucking:
    async def test_set_ducking_validates_and_sets(self, player):
        player.set_ducking(0.3)
        assert player.duck_level == 0.3

    async def test_set_ducking_invalid_raises(self, player):
        with pytest.raises(ValueError):
            player.set_ducking(1.5)


class TestDiscordPlayerDuckingBehavior:
    async def test_default_duck_level_keeps_background_at_full_volume(
        self, make_streamed_player, voice_client, track, bg_track
    ):
        player = make_streamed_player(
            [FakeStreamProcess(3, value=0), FakeStreamProcess(3, value=1000)]
        )
        await player.play(track)
        await player.add_background_source(bg_track)

        # background_volume default 0.5, no ducking -> 1000 * 0.5
        assert _first_sample(voice_client._source.read()) == 500

    async def test_ducking_lowers_background_while_foreground_plays(
        self, make_streamed_player, voice_client, track, bg_track
    ):
        player = make_streamed_player(
            [FakeStreamProcess(3, value=0), FakeStreamProcess(3, value=1000)]
        )
        await player.play(track)
        await player.add_background_source(bg_track)

        player.set_ducking(0.5)

        # 1000 * background_volume(0.5) * duck(0.5) = 250
        assert _first_sample(voice_client._source.read()) == 250

    async def test_ducking_multiplies_with_background_volume(
        self, make_streamed_player, voice_client, track, bg_track
    ):
        player = make_streamed_player(
            [FakeStreamProcess(3, value=0), FakeStreamProcess(3, value=1000)]
        )
        await player.play(track)
        await player.add_background_source(bg_track)

        player.set_background_volume(0.4)
        player.set_ducking(0.5)

        # 1000 * bg_volume(0.4) * duck(0.5) = 200
        assert _first_sample(voice_client._source.read()) == 200

    async def test_background_returns_to_full_when_foreground_ends(
        self, make_streamed_player, voice_client, track, bg_track
    ):
        player = make_streamed_player(
            [FakeStreamProcess(1, value=0), FakeStreamProcess(5, value=1000)]
        )
        await player.play(track)
        await player.add_background_source(bg_track)
        player.set_ducking(0.5)

        source = voice_client._source
        source.read()  # foreground still active -> background ducked
        source.read()  # foreground stream ends here -> un-duck applied

        # background back to full background_volume(0.5): 1000 * 0.5 = 500
        assert _first_sample(source.read()) == 500


class TestDiscordPlayerFactory:
    def test_create_player(self):
        from harpi.infrastructure.discord_player import DiscordPlayerFactory

        factory = DiscordPlayerFactory()
        player = factory.create_player(resolver=FakeResolver())
        assert isinstance(player, type(player))
        assert player.playing is None
