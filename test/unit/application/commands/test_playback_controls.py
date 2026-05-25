import pytest
from harpi.application.commands.skip import SkipCommand, SkipCommandHandler
from harpi.application.commands.pause import PauseCommand, PauseCommandHandler
from harpi.application.commands.resume import ResumeCommand, ResumeCommandHandler
from harpi.application.commands.stop import StopCommand, StopCommandHandler

from harpi.application.player_service import PlayerService
from harpi.domain.track import Track, Source
from harpi.application.ports.audio import AudioResolverProtocol, AudioPlayerProtocol


class FakeAudioResolver(AudioResolverProtocol):
    async def resolve(self, link: str) -> Track:
        return Track(
            link=link,
            title="Mocked Track",
            duration=3600,
            source=Source.YOUTUBE,
            resolved=True,
        )


class FakeAudioPlayer(AudioPlayerProtocol):
    def __init__(self):
        self._playing = None
        self.background_tracks = []
        self.is_paused = False
        self.is_stopped = False

    @property
    def playing(self):
        return self._playing

    def play(self, track: Track):
        self._playing = track
        self.is_stopped = False
        self.is_paused = False

    def pause(self) -> None:
        self.is_paused = True

    def resume(self) -> None:
        self.is_paused = False

    def stop(self) -> None:
        self._playing = None
        self.is_stopped = True


@pytest.fixture
def player_service():
    return PlayerService(resolver=FakeAudioResolver(), player=FakeAudioPlayer())


@pytest.mark.asyncio
async def test_skip_command_success(player_service: PlayerService):
    # Setup state
    await player_service.play("https://youtu.be/first")
    await player_service.play("https://youtu.be/second")

    handler = SkipCommandHandler(player_service=player_service)
    result = await handler.handle(SkipCommand())

    assert result == "Música pulada."
    # Real validation: next track is playing
    assert player_service._player.playing is not None
    assert player_service._player.playing.link == "https://youtu.be/second"


@pytest.mark.asyncio
async def test_pause_command_success(player_service: PlayerService):
    await player_service.play("https://youtu.be/first")
    assert player_service._player.is_paused is False

    handler = PauseCommandHandler(player_service=player_service)
    result = await handler.handle(PauseCommand())

    assert result == "Música pausada."
    assert player_service._player.is_paused is True


@pytest.mark.asyncio
async def test_resume_command_success(player_service: PlayerService):
    await player_service.play("https://youtu.be/first")
    player_service.pause()
    assert player_service._player.is_paused is True

    handler = ResumeCommandHandler(player_service=player_service)
    result = await handler.handle(ResumeCommand())

    assert result == "Música retomada."
    assert player_service._player.is_paused is False


@pytest.mark.asyncio
async def test_stop_command_success(player_service: PlayerService):
    await player_service.play("https://youtu.be/first")
    await player_service.play("https://youtu.be/second")

    handler = StopCommandHandler(player_service=player_service)
    result = await handler.handle(StopCommand())

    assert result == "Fila limpa e música parada."
    assert len(player_service.queue.tracks) == 0
    assert player_service._player.is_stopped is True
    assert player_service._player.playing is None
