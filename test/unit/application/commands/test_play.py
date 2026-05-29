from test.unit.conftest import FakeResolver, FakePlayer
import pytest

from harpi.application.commands.play import PlayCommand, PlayCommandHandler
from harpi.application.player_service import PlayerService


class TestPlayCommandHandler:
    @pytest.mark.asyncio
    async def test_play_command_success(self):
        player_service = PlayerService(resolver=FakeResolver(), player=FakePlayer())
        handler = PlayCommandHandler(player_service=player_service)
        command = PlayCommand(query="https://youtu.be/wPQEeBAXou0")

        result = await handler.handle(command)

        assert result == "Adicionado: https://youtu.be/wPQEeBAXou0"
        assert len(player_service.queue.tracks) == 1
        current_track = player_service.queue.get_current_track()
        assert current_track is not None
        assert current_track.link == "https://youtu.be/wPQEeBAXou0"
        assert player_service._player.playing is not None
        assert player_service._player.playing.link == "https://youtu.be/wPQEeBAXou0"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "invalid_query",
        [
            "",
            "   ",
            "\t\n",
        ],
    )
    async def test_play_command_missing_query(self, invalid_query: str):
        player_service = PlayerService(resolver=FakeResolver(), player=FakePlayer())
        handler = PlayCommandHandler(player_service=player_service)
        command = PlayCommand(query=invalid_query)

        result = await handler.handle(command)

        assert result == "A URL ou termo de busca não pode estar vazio."
        assert len(player_service.queue.tracks) == 0

    @pytest.mark.asyncio
    async def test_play_command_adds_to_existing_queue(self):
        player_service = PlayerService(resolver=FakeResolver(), player=FakePlayer())
        handler = PlayCommandHandler(player_service=player_service)

        await handler.handle(PlayCommand(query="https://youtu.be/first"))
        await handler.handle(PlayCommand(query="https://youtu.be/second"))

        assert len(player_service.queue.tracks) == 2
        assert player_service._player.playing is not None
        assert player_service._player.playing.link == "https://youtu.be/first"
