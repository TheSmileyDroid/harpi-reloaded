import pytest

from harpi.application.commands.play import PlayCommand, PlayCommandHandler
from harpi.application.player_service import PlayerService

from test.unit.application.test_player_service import FakePlayer, FakeResolver


@pytest.mark.asyncio
async def test_play_command_success():
    player_service = PlayerService(resolver=FakeResolver(), player=FakePlayer())
    handler = PlayCommandHandler(player_service=player_service)
    command = PlayCommand(query="https://youtu.be/wPQEeBAXou0")

    result = await handler.handle(command)

    assert "Adicionado" in result
    assert "https://youtu.be/wPQEeBAXou0" in result

    # Assert state in the real queue and real player!
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
    ],
)
async def test_play_command_missing_query(invalid_query: str):
    player_service = PlayerService(resolver=FakeResolver(), player=FakePlayer())
    handler = PlayCommandHandler(player_service=player_service)
    command = PlayCommand(query=invalid_query)

    result = await handler.handle(command)

    assert result == "A URL ou termo de busca não pode estar vazio."
    assert len(player_service.queue.tracks) == 0
