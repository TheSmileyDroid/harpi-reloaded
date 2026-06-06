import pytest
from harpi.application.commands import Response
from harpi.application.player_service import PlayerService
from harpi.infrastructure.command_router import CommandRouter
from test.unit.conftest import FakeResolver, FakePlayer


def _as_str(response: Response) -> str:
    assert isinstance(response, str)
    return response


@pytest.fixture
def router():
    svc = PlayerService(resolver=FakeResolver(), player=FakePlayer())
    return CommandRouter(player_service=svc)


class TestCommandRouterDispatch:
    @pytest.mark.asyncio
    async def test_play_command_dispatches(self, router: CommandRouter):
        response = await router.dispatch("-play https://youtu.be/abc")
        assert response == "Adicionado: https://youtu.be/abc"

    @pytest.mark.asyncio
    async def test_pause_command_dispatches(self, router: CommandRouter):
        response = await router.dispatch("-pause")
        assert response == "Música pausada."

    @pytest.mark.asyncio
    async def test_skip_command_dispatches(self, router: CommandRouter):
        response = await router.dispatch("-skip")
        assert response == "Música pulada."

    @pytest.mark.asyncio
    async def test_stop_command_dispatches(self, router: CommandRouter):
        response = await router.dispatch("-stop")
        assert response == "Fila limpa e música parada."

    @pytest.mark.asyncio
    async def test_resume_command_dispatches(self, router: CommandRouter):
        response = await router.dispatch("-resume")
        assert response == "Música retomada."

    @pytest.mark.asyncio
    async def test_unknown_command_returns_help(self, router: CommandRouter):
        response = await router.dispatch("-invalid")
        assert response is not None
        msg = _as_str(response).lower()
        assert "help" in msg or "comandos" in msg

    @pytest.mark.asyncio
    async def test_empty_string_returns_help(self, router: CommandRouter):
        response = await router.dispatch("")
        assert response is not None
        msg = _as_str(response).lower()
        assert "help" in msg or "comandos" in msg

    @pytest.mark.asyncio
    async def test_message_without_prefix_returns_none(self, router: CommandRouter):
        response = await router.dispatch("just some text")
        assert response is None

    @pytest.mark.asyncio
    async def test_command_is_case_insensitive(self, router: CommandRouter):
        response = await router.dispatch("-Pause")
        assert response == "Música pausada."

    @pytest.mark.asyncio
    async def test_play_command_without_args_returns_error(self, router: CommandRouter):
        response = await router.dispatch("-play")
        assert response is not None
        msg = _as_str(response).lower()
        assert "vazio" in msg or "url" in msg


class TestCommandRouterCustomPrefix:
    @pytest.mark.asyncio
    async def test_custom_prefix(self):
        svc = PlayerService(resolver=FakeResolver(), player=FakePlayer())
        router = CommandRouter(player_service=svc, prefix="!")
        response = await router.dispatch("!play https://youtu.be/abc")
        assert response == "Adicionado: https://youtu.be/abc"

    @pytest.mark.asyncio
    async def test_custom_prefix_ignores_other_prefix(self):
        svc = PlayerService(resolver=FakeResolver(), player=FakePlayer())
        router = CommandRouter(player_service=svc, prefix="!")
        response = await router.dispatch("-play https://youtu.be/abc")
        assert response is None
