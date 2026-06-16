from collections.abc import Callable, Coroutine
from typing import Any

import pytest
from harpi.application.commands import Response
from harpi.application.player_service import PlayerService
from harpi.infrastructure.discord_bot import HarpiBot
from harpi.infrastructure.command_router import CommandRouter


def _as_str(response: Response) -> str:
    assert isinstance(response, str)
    return response


class _FakeVoiceChannel:
    def __init__(self, name: str = "General"):
        self.name = name


class _FakeVoiceState:
    def __init__(self, channel: _FakeVoiceChannel | None = None):
        self.channel = channel


class _FakeGuild:
    def __init__(self, guild_id: int = 1):
        self.id = guild_id
        self.voice_client = None


class _FakeDiscordMessage:
    def __init__(
        self,
        content: str,
        guild: _FakeGuild | None = None,
        voice: _FakeVoiceState | None = None,
        bot: bool = False,
    ):
        self.content = content
        self.guild = guild
        self.author = _FakeAuthor(voice=voice, bot=bot)


class _FakeAuthor:
    def __init__(self, voice: _FakeVoiceState | None = None, bot: bool = False):
        self.bot = bot
        self.voice = voice


class _FakePlayerWithConnection:
    def __init__(self):
        self._playing: Any = None
        self.background_tracks: list[Any] = []
        self.is_paused: bool = False
        self.is_stopped: bool = False
        self.volume: float = 1.0
        self.background_volume: float = 0.5
        self.is_ducking: bool = False
        self._duck_level: float = 0.2
        self._saved_background_volume: float | None = None
        self._voice_client: Any = None
        self._position: float | None = None
        self._connected_channel: _FakeVoiceChannel | None = None

    @property
    def playing(self) -> Any:
        return self._playing

    @property
    def position(self) -> float | None:
        return self._position

    @property
    def is_connected(self) -> bool:
        return self._voice_client is not None

    @property
    def connected_channel(self) -> _FakeVoiceChannel | None:
        return self._connected_channel

    async def play(
        self,
        track: Any,
        on_finish: Callable[[], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        self._playing = track
        self.is_stopped = False
        self.is_paused = False

    async def pause(self) -> None:
        self.is_paused = True

    async def resume(self) -> None:
        self.is_paused = False

    async def stop(self) -> None:
        self._playing = None
        self.is_stopped = True

    def set_volume(self, volume: float) -> None:
        self.volume = volume

    def set_background_volume(self, volume: float) -> None:
        self.background_volume = volume

    def set_ducking(self, duck_level: float) -> None:
        self._duck_level = duck_level

    async def duck(self) -> None:
        if self.is_ducking:
            return
        self._saved_background_volume = self.background_volume
        self.background_volume = self._duck_level
        self.is_ducking = True

    async def unduck(self) -> None:
        if not self.is_ducking:
            return
        if self._saved_background_volume is not None:
            self.background_volume = self._saved_background_volume
            self._saved_background_volume = None
        self.is_ducking = False

    def set_voice_client(self, vc: Any) -> None:
        self._voice_client = vc
        self.is_stopped = False
        self.is_paused = False

    async def connect(self, channel: _FakeVoiceChannel) -> None:
        self._voice_client = object()
        self._connected_channel = channel
        self.is_stopped = True
        self.is_paused = False

    async def add_background_source(self, track: Any) -> None:
        self.background_tracks.append(track)

    def remove_background_source(self, index: int) -> Any:
        return self.background_tracks.pop(index)


@pytest.fixture
def bot():
    from test.unit.conftest import FakeResolver, FakePlayer

    svc = PlayerService(resolver=FakeResolver(), player=FakePlayer())
    return HarpiBot(player_service=svc)


def _bot_with_resolver() -> HarpiBot:
    from test.unit.conftest import FakeResolver

    return HarpiBot(resolver=FakeResolver(), prefix="-")


def _inject_guild_state(
    bot: HarpiBot, guild_id: int = 1
) -> tuple[_FakePlayerWithConnection, CommandRouter]:
    from test.unit.conftest import FakeResolver

    player = _FakePlayerWithConnection()
    service = PlayerService(resolver=FakeResolver(), player=player)
    router = CommandRouter(player_service=service, prefix="-")
    bot._guild_players[guild_id] = player  # ty: ignore
    bot._guild_routers[guild_id] = router
    return player, router


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
class TestHarpiBotVoiceConnection:
    @pytest.mark.asyncio
    async def test_play_without_voice_returns_error(self):
        bot = _bot_with_resolver()
        _inject_guild_state(bot)
        guild = _FakeGuild()
        msg = _FakeDiscordMessage(
            content="-play https://youtu.be/abc", guild=guild, voice=None
        )

        response = await bot.handle_discord_message(msg)

        assert response is not None
        assert "canal de voz" in _as_str(response)

    @pytest.mark.asyncio
    async def test_play_with_voice_connects_and_dispatches(self):
        bot = _bot_with_resolver()
        player, _ = _inject_guild_state(bot)
        channel = _FakeVoiceChannel("Test Room")
        guild = _FakeGuild()
        msg = _FakeDiscordMessage(
            content="-play https://youtu.be/abc",
            guild=guild,
            voice=_FakeVoiceState(channel),
        )

        response = await bot.handle_discord_message(msg)

        assert response is not None
        assert "Adicionado" in _as_str(response)
        assert player.is_connected
        assert player.connected_channel is channel

    @pytest.mark.asyncio
    async def test_non_voice_command_does_not_connect(self):
        bot = _bot_with_resolver()
        player, _ = _inject_guild_state(bot)
        guild = _FakeGuild()
        msg = _FakeDiscordMessage(
            content="-queue", guild=guild, voice=None
        )

        response = await bot.handle_discord_message(msg)

        assert response is not None
        assert not player.is_connected

    @pytest.mark.asyncio
    async def test_already_connected_skips_reconnection(self):
        bot = _bot_with_resolver()
        player, _ = _inject_guild_state(bot)
        player.set_voice_client(object())
        channel = _FakeVoiceChannel("Test Room")
        guild = _FakeGuild()
        msg = _FakeDiscordMessage(
            content="-play https://youtu.be/abc",
            guild=guild,
            voice=_FakeVoiceState(channel),
        )

        response = await bot.handle_discord_message(msg)

        assert response is not None
        assert "Adicionado" in _as_str(response)
        assert player.connected_channel is None


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
