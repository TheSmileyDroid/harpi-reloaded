import pytest
from harpi.application.player_service import PlayerService
from test.unit.conftest import FakeResolver, FakePlayer
from harpi.domain.loop_mode import LoopMode


@pytest.fixture
def service():
    return PlayerService(resolver=FakeResolver(), player=FakePlayer())


@pytest.mark.asyncio
class TestVolumeCommand:
    async def test_volume_sets_level(self, service: PlayerService):
        from harpi.application.commands.volume import handle_volume

        result = await handle_volume(service, "0.5")
        assert isinstance(result, str)
        assert "50%" in result
        assert service._player.volume == 0.5

    async def test_volume_minimum(self, service: PlayerService):
        from harpi.application.commands.volume import handle_volume

        result = await handle_volume(service, "0.0")
        assert isinstance(result, str)
        assert "0%" in result
        assert service._player.volume == 0.0

    async def test_volume_maximum(self, service: PlayerService):
        from harpi.application.commands.volume import handle_volume

        result = await handle_volume(service, "1.0")
        assert isinstance(result, str)
        assert "100%" in result
        assert service._player.volume == 1.0

    async def test_volume_invalid_returns_error(self, service: PlayerService):
        from harpi.application.commands.volume import handle_volume

        result = await handle_volume(service, "1.5")
        assert isinstance(result, str)
        assert "deve ser um número" in result or "must be between" in result

    async def test_volume_non_numeric_returns_error(self, service: PlayerService):
        from harpi.application.commands.volume import handle_volume

        result = await handle_volume(service, "abc")
        assert isinstance(result, str)
        assert "deve ser um número" in result

    async def test_volume_empty_returns_error(self, service: PlayerService):
        from harpi.application.commands.volume import handle_volume

        result = await handle_volume(service, "")
        assert isinstance(result, str)
        assert "Especifique" in result


@pytest.mark.asyncio
class TestBgVolumeCommand:
    async def test_bgvolume_sets_level(self, service: PlayerService):
        from harpi.application.commands.volume import handle_bgvolume

        result = await handle_bgvolume(service, "0.3")
        assert isinstance(result, str)
        assert "30%" in result
        assert service._player.background_volume == 0.3

    async def test_bgvolume_empty_returns_error(self, service: PlayerService):
        from harpi.application.commands.volume import handle_bgvolume

        result = await handle_bgvolume(service, "")
        assert isinstance(result, str)
        assert "Especifique" in result


@pytest.mark.asyncio
class TestDuckCommand:
    async def test_duck_sets_level(self, service: PlayerService):
        from harpi.application.commands.volume import handle_duck
        from test.unit.conftest import FakePlayer

        result = await handle_duck(service, "0.2")
        assert isinstance(result, str)
        assert "20%" in result
        player = service._player
        assert isinstance(player, FakePlayer)
        assert player._duck_level == 0.2

    async def test_duck_empty_returns_error(self, service: PlayerService):
        from harpi.application.commands.volume import handle_duck

        result = await handle_duck(service, "")
        assert isinstance(result, str)
        assert "Especifique" in result


@pytest.mark.asyncio
class TestLoopCommand:
    async def test_loop_no_arg_cycles(self, service: PlayerService):
        from harpi.application.commands.loop import handle_loop

        assert service.queue.loop_mode == LoopMode.OFF
        result = await handle_loop(service, "")
        assert isinstance(result, str)
        assert "off → track" in result
        assert service.queue.loop_mode == LoopMode.TRACK

    async def test_loop_set_off(self, service: PlayerService):
        from harpi.application.commands.loop import handle_loop

        service.queue.set_loop_mode(LoopMode.TRACK)
        result = await handle_loop(service, "off")
        assert isinstance(result, str)
        assert "off" in result
        assert service.queue.loop_mode == LoopMode.OFF

    async def test_loop_set_track(self, service: PlayerService):
        from harpi.application.commands.loop import handle_loop

        result = await handle_loop(service, "track")
        assert isinstance(result, str)
        assert "track" in result
        assert service.queue.loop_mode == LoopMode.TRACK

    async def test_loop_set_queue(self, service: PlayerService):
        from harpi.application.commands.loop import handle_loop

        result = await handle_loop(service, "queue")
        assert isinstance(result, str)
        assert "queue" in result
        assert service.queue.loop_mode == LoopMode.QUEUE

    async def test_loop_invalid_mode(self, service: PlayerService):
        from harpi.application.commands.loop import handle_loop

        result = await handle_loop(service, "invalid")
        assert isinstance(result, str)
        assert "Modos válidos" in result


@pytest.mark.asyncio
class TestRmCommand:
    async def test_rm_removes_track(self, service: PlayerService):
        from harpi.application.commands.rm import handle_rm

        await service.play("https://youtu.be/abc")
        await service.play("https://youtu.be/def")
        result = await handle_rm(service, "0")
        assert isinstance(result, str)
        assert "removida" in result
        assert len(service.queue.tracks) == 1
        assert service.queue.tracks[0].link == "https://youtu.be/def"

    async def test_rm_invalid_index(self, service: PlayerService):
        from harpi.application.commands.rm import handle_rm

        await service.play("https://youtu.be/abc")
        result = await handle_rm(service, "5")
        assert isinstance(result, str)
        assert "inválido" in result

    async def test_rm_non_numeric(self, service: PlayerService):
        from harpi.application.commands.rm import handle_rm

        result = await handle_rm(service, "abc")
        assert isinstance(result, str)
        assert "deve ser um número" in result

    async def test_rm_empty_args(self, service: PlayerService):
        from harpi.application.commands.rm import handle_rm

        result = await handle_rm(service, "")
        assert isinstance(result, str)
        assert "Especifique" in result

    async def test_rm_negative_index(self, service: PlayerService):
        from harpi.application.commands.rm import handle_rm

        await service.play("https://youtu.be/abc")
        result = await handle_rm(service, "-1")
        assert isinstance(result, str)
        assert "inválido" in result

    async def test_rm_removes_only_one_duplicate(self, service: PlayerService):
        from harpi.application.commands.rm import handle_rm

        await service.play("https://youtu.be/abc")
        await service.play("https://youtu.be/abc")
        assert len(service.queue.tracks) == 2
        result = await handle_rm(service, "0")
        assert isinstance(result, str)
        assert "removida" in result
        assert len(service.queue.tracks) == 1
