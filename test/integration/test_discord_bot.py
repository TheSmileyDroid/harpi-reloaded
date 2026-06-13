import pytest
from harpi.application.commands import Response
from harpi.application.player_service import PlayerService
from harpi.infrastructure.discord_bot import HarpiBot


def _as_str(response: Response) -> str:
    assert isinstance(response, str)
    return response


@pytest.fixture
def bot():
    from test.unit.conftest import FakeResolver, FakePlayer

    svc = PlayerService(resolver=FakeResolver(), player=FakePlayer())
    return HarpiBot(player_service=svc)


@pytest.mark.integration
class TestHarpiBotMessageHandling:
    @pytest.mark.asyncio
    async def test_play_command_responds(self, bot: HarpiBot):
        response = await bot.on_message(
            "-play https://youtu.be/abc", author_is_bot=False
        )
        assert response is not None
        assert "Adicionado" in _as_str(response)

    @pytest.mark.asyncio
    async def test_bot_message_is_ignored(self, bot: HarpiBot):
        response = await bot.on_message(
            "-play https://youtu.be/abc", author_is_bot=True
        )
        assert response is None

    @pytest.mark.asyncio
    async def test_pause_command_responds(self, bot: HarpiBot):
        response = await bot.on_message("-pause", author_is_bot=False)
        assert response is not None
        assert "pausada" in _as_str(response)

    @pytest.mark.asyncio
    async def test_skip_command_responds(self, bot: HarpiBot):
        response = await bot.on_message("-skip", author_is_bot=False)
        assert response is not None
        assert "pulada" in _as_str(response)

    @pytest.mark.asyncio
    async def test_stop_command_responds(self, bot: HarpiBot):
        response = await bot.on_message("-stop", author_is_bot=False)
        assert response is not None
        assert "parada" in _as_str(response)

    @pytest.mark.asyncio
    async def test_resume_command_responds(self, bot: HarpiBot):
        response = await bot.on_message("-resume", author_is_bot=False)
        assert response is not None
        assert "retomada" in _as_str(response)

    @pytest.mark.asyncio
    async def test_unknown_command_returns_help(self, bot: HarpiBot):
        response = await bot.on_message("-invalid", author_is_bot=False)
        assert response is not None
        msg = _as_str(response).lower()
        assert "help" in msg or "comandos" in msg

    @pytest.mark.asyncio
    async def test_text_without_prefix_returns_none(self, bot: HarpiBot):
        response = await bot.on_message("just some random text", author_is_bot=False)
        assert response is None

    @pytest.mark.asyncio
    async def test_play_error_returns_error_message(self):
        from test.unit.conftest import FakeResolver, FakePlayer

        resolver = FakeResolver()
        resolver.set_failure("https://youtu.be/bad", Exception("Network error"))
        svc = PlayerService(resolver=resolver, player=FakePlayer())
        bot = HarpiBot(player_service=svc)

        response = await bot.on_message(
            "-play https://youtu.be/bad", author_is_bot=False
        )
        assert response is not None
        msg = _as_str(response).lower()
        assert "error" in msg or "erro" in msg


@pytest.mark.integration
class TestHarpiBotCustomTokenAndPrefix:
    @pytest.mark.asyncio
    async def test_custom_prefix(self):
        from test.unit.conftest import FakeResolver, FakePlayer

        svc = PlayerService(resolver=FakeResolver(), player=FakePlayer())
        bot = HarpiBot(player_service=svc, prefix="!")

        response = await bot.on_message(
            "!play https://youtu.be/abc", author_is_bot=False
        )
        assert response is not None
        assert "Adicionado" in _as_str(response)
