import pytest
from harpi.application.player_service import PlayerService
from test.unit.conftest import FakeResolver, FakePlayer
from harpi.application.ports.audio import AudioResolverProtocol
from harpi.domain.track import Track, Source


class NoTitleResolver(AudioResolverProtocol):
    async def resolve(self, link: str) -> Track:
        return Track(link=link, source=Source.YOUTUBE, duration=120, resolved=True)


@pytest.fixture
def service():
    return PlayerService(resolver=FakeResolver(), player=FakePlayer())


@pytest.mark.asyncio
class TestQueueCommand:
    async def test_queue_empty(self):
        from harpi.application.commands.handlers import handle_queue
        from harpi.application.commands import EmbedData

        svc = PlayerService(resolver=FakeResolver(), player=FakePlayer())
        result = await handle_queue(svc, "")

        assert isinstance(result, EmbedData)
        assert result.description == "Nada tocando no momento."
        assert result.footer == "Fila: 0 músicas | Loop: off"

    async def test_queue_with_one_track(self, service: PlayerService):
        await service.play("https://youtu.be/abc")
        from harpi.application.commands.handlers import handle_queue
        from harpi.application.commands import EmbedData

        result = await handle_queue(service, "")

        assert isinstance(result, EmbedData)
        assert "Fake Track (02:00)" in result.description
        assert result.footer == "Total: 1 músicas | Loop: off"

    async def test_queue_with_multiple_tracks(self, service: PlayerService):
        await service.play("https://youtu.be/abc")
        await service.play("https://youtu.be/def")
        await service.play("https://youtu.be/ghi")
        from harpi.application.commands.handlers import handle_queue
        from harpi.application.commands import EmbedData

        result = await handle_queue(service, "")

        assert isinstance(result, EmbedData)
        lines = result.description.split("\n")
        assert "Fake Track (02:00)" in lines[0]
        assert "1. Fake Track (02:00)" in lines[1]
        assert "2. Fake Track (02:00)" in lines[2]

    async def test_queue_shows_playing_track_first(self, service: PlayerService):
        await service.play("https://youtu.be/abc")
        await service.play("https://youtu.be/ghi")
        from harpi.application.commands.handlers import handle_queue
        from harpi.application.commands import EmbedData

        result = await handle_queue(service, "")

        assert isinstance(result, EmbedData)
        lines = result.description.split("\n")
        assert "abc" in lines[0] or "Fake Track" in lines[0]
        assert "1." in lines[1]

    async def test_queue_track_without_title_shows_fallback_current(self):
        svc = PlayerService(resolver=NoTitleResolver(), player=FakePlayer())
        await svc.play("https://youtu.be/abc")
        from harpi.application.commands.handlers import handle_queue
        from harpi.application.commands import EmbedData

        result = await handle_queue(svc, "")

        assert isinstance(result, EmbedData)
        assert "Desconhecida" in result.description
        assert "Desconhecida (02:00)" in result.description

    async def test_queue_track_without_title_shows_fallback_upcoming(self):
        svc = PlayerService(resolver=NoTitleResolver(), player=FakePlayer())
        await svc.play("https://youtu.be/abc")
        await svc.play("https://youtu.be/def")
        from harpi.application.commands.handlers import handle_queue
        from harpi.application.commands import EmbedData

        result = await handle_queue(svc, "")

        assert isinstance(result, EmbedData)
        assert "1. Desconhecida (02:00)" in result.description

    async def test_format_duration_returns_formatted_time(self):
        from harpi.application.commands.handlers import _format_duration

        assert _format_duration(0) == "00:00"
        assert _format_duration(60) == "01:00"
        assert _format_duration(3661) == "61:01"
        assert _format_duration(None) == "--:--"


@pytest.mark.asyncio
class TestRegistry:
    async def test_register_collects_handlers(self):
        from harpi.application.commands import get_handlers

        handlers = get_handlers()
        assert "play" in handlers
        assert "pause" in handlers
        assert "skip" in handlers
        assert "stop" in handlers
        assert "resume" in handlers
        assert "queue" in handlers

    async def test_registered_handlers_are_callable(self):
        from harpi.application.commands import get_handlers

        for name, handler in get_handlers().items():
            assert callable(handler)

    async def test_register_new_handler_after_import(self):
        from harpi.application.commands import register, get_handlers

        @register("__test_only__")
        async def _test_handler(service, args: str) -> str:
            return "ok"

        handlers = get_handlers()
        assert "__test_only__" in handlers
        assert callable(handlers["__test_only__"])

    async def test_register_includes_background_commands(self):
        from harpi.application.commands import get_handlers

        handlers = get_handlers()
        assert "bg" in handlers
        assert "bgrm" in handlers


@pytest.mark.asyncio
class TestBackgroundCommands:
    async def test_bg_add_handler(self, service: PlayerService):
        from harpi.application.commands.handlers import handle_bg

        result = await handle_bg(service, "https://youtu.be/abc")
        assert isinstance(result, str)
        assert len(service.queue.background_tracks) == 1
        assert service.queue.background_tracks[0].link == "https://youtu.be/abc"

    async def test_bg_add_empty_args_returns_error(self, service: PlayerService):
        from harpi.application.commands.handlers import handle_bg

        result = await handle_bg(service, "")
        assert isinstance(result, str)
        assert "vazio" in result

    async def test_bgrm_handler_by_index(self, service: PlayerService):
        from harpi.application.commands.handlers import handle_bgrm

        await service.add_background_track("https://youtu.be/abc")
        await service.add_background_track("https://youtu.be/def")

        result = await handle_bgrm(service, "0")
        assert isinstance(result, str)
        assert len(service.queue.background_tracks) == 1
        assert service.queue.background_tracks[0].link == "https://youtu.be/def"

    async def test_bgrm_handler_invalid_index_returns_error(
        self, service: PlayerService
    ):
        from harpi.application.commands.handlers import handle_bgrm

        result = await handle_bgrm(service, "abc")
        assert isinstance(result, str)
        assert "número" in result

    async def test_bgrm_handler_out_of_bounds_returns_error(
        self, service: PlayerService
    ):
        from harpi.application.commands.handlers import handle_bgrm

        result = await handle_bgrm(service, "5")
        assert isinstance(result, str)
        assert "inválido" in result

    async def test_bgrm_handler_empty_args_returns_error(self, service: PlayerService):
        from harpi.application.commands.handlers import handle_bgrm

        result = await handle_bgrm(service, "")
        assert isinstance(result, str)
        assert "índice" in result


@pytest.mark.asyncio
class TestQueueBackgroundEmbed:
    async def test_queue_shows_background_tracks_with_positions(
        self, service: PlayerService
    ):
        from harpi.application.commands.handlers import handle_queue
        from harpi.application.commands import EmbedData

        await service.play("https://youtu.be/abc")
        await service.add_background_track("https://youtu.be/bg1")

        result = await handle_queue(service, "")
        assert isinstance(result, EmbedData)
        assert "Músicas de fundo" in result.description
        assert "0." in result.description
        assert "Fundo: 1" in result.footer

    async def test_queue_shows_background_tracks_when_nothing_playing(
        self, service: PlayerService
    ):
        from harpi.application.commands.handlers import handle_queue
        from harpi.application.commands import EmbedData

        await service.add_background_track("https://youtu.be/bg1")

        result = await handle_queue(service, "")
        assert isinstance(result, EmbedData)
        assert "Nada tocando no momento." in result.description
        assert "Músicas de fundo" in result.description
