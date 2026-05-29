import pytest
from harpi.application.commands.skip import SkipCommand, SkipCommandHandler
from harpi.application.commands.pause import PauseCommand, PauseCommandHandler
from harpi.application.commands.resume import ResumeCommand, ResumeCommandHandler
from harpi.application.commands.stop import StopCommand, StopCommandHandler

from harpi.application.player_service import PlayerService
from test.unit.conftest import FakeResolver, FakePlayer


@pytest.fixture
def player_service():
    return PlayerService(resolver=FakeResolver(), player=FakePlayer())


class TestSkipCommandHandler:
    @pytest.mark.asyncio
    async def test_skip_command_success(self, player_service: PlayerService):
        await player_service.play("https://youtu.be/first")
        await player_service.play("https://youtu.be/second")

        handler = SkipCommandHandler(player_service=player_service)
        result = await handler.handle(SkipCommand())

        assert result == "Música pulada."
        assert player_service._player.playing is not None
        assert player_service._player.playing.link == "https://youtu.be/second"

    @pytest.mark.asyncio
    async def test_skip_command_empty_queue(self, player_service: PlayerService):
        handler = SkipCommandHandler(player_service=player_service)
        result = await handler.handle(SkipCommand())
        assert result == "Música pulada."
        assert player_service._player.playing is None


class TestPauseCommandHandler:
    @pytest.mark.asyncio
    async def test_pause_command_success(self, player_service: PlayerService):
        await player_service.play("https://youtu.be/first")
        assert player_service._player.is_paused is False

        handler = PauseCommandHandler(player_service=player_service)
        result = await handler.handle(PauseCommand())

        assert result == "Música pausada."
        assert player_service._player.is_paused is True


class TestResumeCommandHandler:
    @pytest.mark.asyncio
    async def test_resume_command_success(self, player_service: PlayerService):
        await player_service.play("https://youtu.be/first")
        player_service.pause()
        assert player_service._player.is_paused is True

        handler = ResumeCommandHandler(player_service=player_service)
        result = await handler.handle(ResumeCommand())

        assert result == "Música retomada."
        assert player_service._player.is_paused is False


class TestStopCommandHandler:
    @pytest.mark.asyncio
    async def test_stop_command_success(self, player_service: PlayerService):
        await player_service.play("https://youtu.be/first")
        await player_service.play("https://youtu.be/second")

        handler = StopCommandHandler(player_service=player_service)
        result = await handler.handle(StopCommand())

        assert result == "Fila limpa e música parada."
        assert len(player_service.queue.tracks) == 0
        assert player_service._player.is_stopped is True
        assert player_service._player.playing is None

    @pytest.mark.asyncio
    async def test_stop_command_empty_queue(self, player_service: PlayerService):
        handler = StopCommandHandler(player_service=player_service)
        result = await handler.handle(StopCommand())
        assert result == "Fila limpa e música parada."
        assert player_service._player.is_stopped is True
