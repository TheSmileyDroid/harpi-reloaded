import pytest
from harpi.application.ports.audio import AudioPlayerProtocol
from harpi.domain.track import Track, Source


class FakeAudioSource:
    pass


class FakeVoiceClient:
    def __init__(self):
        self._is_playing = False
        self._is_paused = False
        self._source = None
        self._after = None

    def play(self, source, after=None):
        self._source = source
        self._after = after
        self._is_playing = True
        self._is_paused = False

    def pause(self):
        self._is_paused = True
        self._is_playing = False

    def resume(self):
        self._is_paused = False
        self._is_playing = True

    def stop(self):
        self._is_playing = False
        self._is_paused = False

    def is_playing(self):
        return self._is_playing

    def is_paused(self):
        return self._is_paused


@pytest.fixture
def voice_client():
    return FakeVoiceClient()


@pytest.fixture
def source_factory():
    async def factory(track: Track) -> FakeAudioSource:
        return FakeAudioSource()
    return factory


@pytest.fixture
def player(voice_client, source_factory):
    from harpi.infrastructure.discord_player import DiscordPlayer
    return DiscordPlayer(voice_client=voice_client, source_factory=source_factory)


@pytest.fixture
def track():
    return Track(
        link="https://youtu.be/abc123",
        title="Test Track",
        duration=120,
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
    async def test_play_sets_playing_to_track(self, player: AudioPlayerProtocol, track: Track):
        await player.play(track)
        assert player.playing is track

    async def test_play_calls_voice_client_play(self, player: AudioPlayerProtocol, track: Track, voice_client: FakeVoiceClient):
        await player.play(track)
        assert voice_client.is_playing()

    async def test_play_clears_is_stopped(self, player: AudioPlayerProtocol, track: Track):
        await player.stop()
        await player.play(track)
        assert player.is_stopped is False

    async def test_play_clears_is_paused(self, player: AudioPlayerProtocol, track: Track):
        await player.pause()
        await player.play(track)
        assert player.is_paused is False

    async def test_play_passes_source_to_voice_client(self, player: AudioPlayerProtocol, track: Track, voice_client: FakeVoiceClient):
        await player.play(track)
        assert voice_client._source is not None


class TestDiscordPlayerPause:
    async def test_pause_sets_is_paused(self, player: AudioPlayerProtocol, track: Track):
        await player.play(track)
        await player.pause()
        assert player.is_paused is True

    async def test_pause_calls_voice_client_pause(self, player: AudioPlayerProtocol, track: Track, voice_client: FakeVoiceClient):
        await player.play(track)
        await player.pause()
        assert voice_client.is_paused()


class TestDiscordPlayerResume:
    async def test_resume_clears_is_paused(self, player: AudioPlayerProtocol, track: Track):
        await player.play(track)
        await player.pause()
        await player.resume()
        assert player.is_paused is False

    async def test_resume_calls_voice_client_resume(self, player: AudioPlayerProtocol, track: Track, voice_client: FakeVoiceClient):
        await player.play(track)
        await player.pause()
        await player.resume()
        assert not voice_client.is_paused()


class TestDiscordPlayerStop:
    async def test_stop_sets_is_stopped(self, player: AudioPlayerProtocol, track: Track):
        await player.play(track)
        await player.stop()
        assert player.is_stopped is True

    async def test_stop_clears_playing(self, player: AudioPlayerProtocol, track: Track):
        await player.play(track)
        await player.stop()
        assert player.playing is None

    async def test_stop_calls_voice_client_stop(self, player: AudioPlayerProtocol, track: Track, voice_client: FakeVoiceClient):
        await player.play(track)
        await player.stop()
        assert not voice_client.is_playing()
        assert not voice_client.is_paused()


class TestDiscordPlayerErrors:
    async def test_play_without_voice_client_raises(self, track: Track):
        from harpi.infrastructure.discord_player import DiscordPlayer
        player = DiscordPlayer()

        with pytest.raises(RuntimeError, match="Not connected"):
            await player.play(track)

    async def test_play_raises_when_source_factory_fails(self, voice_client, track: Track):
        from harpi.infrastructure.discord_player import DiscordPlayer

        async def failing_factory(_track: Track):
            raise ValueError("No audio stream available")

        player = DiscordPlayer(voice_client=voice_client, source_factory=failing_factory)

        with pytest.raises(ValueError, match="No audio stream available"):
            await player.play(track)

    async def test_pause_without_voice_client_raises(self, track: Track):
        from harpi.infrastructure.discord_player import DiscordPlayer
        player = DiscordPlayer()

        with pytest.raises(RuntimeError, match="Not connected"):
            await player.pause()

    async def test_resume_without_voice_client_raises(self, track: Track):
        from harpi.infrastructure.discord_player import DiscordPlayer
        player = DiscordPlayer()

        with pytest.raises(RuntimeError, match="Not connected"):
            await player.resume()

    async def test_stop_without_voice_client_raises(self, track: Track):
        from harpi.infrastructure.discord_player import DiscordPlayer
        player = DiscordPlayer()

        with pytest.raises(RuntimeError, match="Not connected"):
            await player.stop()
