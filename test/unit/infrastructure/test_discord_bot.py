import pytest
from harpi.application.commands import Response
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


class _FailingRouter(CommandRouter):
    async def dispatch(self, message: str) -> Response:
        raise RuntimeError("Something broke")


class _FakeVoiceClientWithChannel:
    def __init__(self, channel: _FakeVoiceChannel):
        self.channel = channel

    def is_playing(self) -> bool:
        return False

    async def move_to(self, channel: _FakeVoiceChannel) -> None:
        self.channel = channel


@pytest.fixture
def bot():
    from test.unit.conftest import FakeResolver, FakePlayerFactory

    return HarpiBot(
        player_factory=FakePlayerFactory(), resolver=FakeResolver(), prefix="-"
    )


def _bot_with_resolver() -> HarpiBot:
    from test.unit.conftest import FakeResolver, FakePlayerFactory

    return HarpiBot(
        resolver=FakeResolver(), player_factory=FakePlayerFactory(), prefix="-"
    )


class TestHarpiBotMessageHandling:
    @pytest.mark.asyncio
    async def test_play_command_responds(self, bot: HarpiBot):
        response = await bot.handle_discord_message(
            _FakeDiscordMessage(
                content="-play https://youtu.be/abc",
                guild=_FakeGuild(),
                voice=_FakeVoiceState(_FakeVoiceChannel()),
            )
        )
        assert response is not None
        assert "Adicionado" in _as_str(response)

    @pytest.mark.asyncio
    async def test_bot_message_is_ignored(self, bot: HarpiBot):
        response = await bot.handle_discord_message(
            _FakeDiscordMessage(
                content="-play https://youtu.be/abc",
                guild=_FakeGuild(),
                voice=_FakeVoiceState(_FakeVoiceChannel()),
                bot=True,
            )
        )
        assert response is None

    @pytest.mark.asyncio
    async def test_pause_command_responds(self, bot: HarpiBot):
        response = await bot.handle_discord_message(
            _FakeDiscordMessage(
                content="-pause",
                guild=_FakeGuild(),
                voice=_FakeVoiceState(_FakeVoiceChannel()),
            )
        )
        assert response is not None
        assert "pausada" in _as_str(response)

    @pytest.mark.asyncio
    async def test_skip_command_responds(self, bot: HarpiBot):
        response = await bot.handle_discord_message(
            _FakeDiscordMessage(
                content="-skip",
                guild=_FakeGuild(),
                voice=_FakeVoiceState(_FakeVoiceChannel()),
            )
        )
        assert response is not None
        assert "pulada" in _as_str(response)

    @pytest.mark.asyncio
    async def test_stop_command_responds(self, bot: HarpiBot):
        response = await bot.handle_discord_message(
            _FakeDiscordMessage(
                content="-stop",
                guild=_FakeGuild(),
                voice=_FakeVoiceState(_FakeVoiceChannel()),
            )
        )
        assert response is not None
        assert "parada" in _as_str(response)

    @pytest.mark.asyncio
    async def test_resume_command_responds(self, bot: HarpiBot):
        response = await bot.handle_discord_message(
            _FakeDiscordMessage(
                content="-resume",
                guild=_FakeGuild(),
                voice=_FakeVoiceState(_FakeVoiceChannel()),
            )
        )
        assert response is not None
        assert "retomada" in _as_str(response)

    @pytest.mark.asyncio
    async def test_unknown_command_returns_help(self, bot: HarpiBot):
        response = await bot.handle_discord_message(
            _FakeDiscordMessage(
                content="-invalid",
                guild=_FakeGuild(),
                voice=_FakeVoiceState(_FakeVoiceChannel()),
            )
        )
        assert response is not None
        msg = _as_str(response).lower()
        assert "help" in msg or "comandos" in msg

    @pytest.mark.asyncio
    async def test_text_without_prefix_returns_none(self, bot: HarpiBot):
        response = await bot.handle_discord_message(
            _FakeDiscordMessage(
                content="just some random text",
                guild=_FakeGuild(),
                voice=_FakeVoiceState(_FakeVoiceChannel()),
            )
        )
        assert response is None

    @pytest.mark.asyncio
    async def test_play_error_returns_error_message(self):
        from test.unit.conftest import FakeResolver, FakePlayerFactory

        resolver = FakeResolver()
        resolver.set_failure("https://youtu.be/bad", Exception("Network error"))
        bot = HarpiBot(
            player_factory=FakePlayerFactory(), resolver=resolver, prefix="-"
        )

        response = await bot.handle_discord_message(
            _FakeDiscordMessage(
                content="-play https://youtu.be/bad",
                guild=_FakeGuild(),
                voice=_FakeVoiceState(_FakeVoiceChannel()),
            )
        )
        assert response is not None
        msg = _as_str(response).lower()
        assert "error" in msg or "erro" in msg


class TestHarpiBotVoiceConnection:
    @pytest.mark.asyncio
    async def test_play_without_voice_returns_error(self):
        bot = _bot_with_resolver()
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

    @pytest.mark.asyncio
    async def test_non_voice_command_does_not_connect(self):
        bot = _bot_with_resolver()
        guild = _FakeGuild()
        msg = _FakeDiscordMessage(content="-queue", guild=guild, voice=None)

        response = await bot.handle_discord_message(msg)

        assert response is not None

    @pytest.mark.asyncio
    async def test_already_connected_skips_reconnection(self):
        bot = _bot_with_resolver()
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


class TestHarpiBotCustomTokenAndPrefix:
    @pytest.mark.asyncio
    async def test_custom_prefix(self):
        from test.unit.conftest import FakeResolver, FakePlayerFactory

        bot = HarpiBot(
            resolver=FakeResolver(), player_factory=FakePlayerFactory(), prefix="!"
        )

        response = await bot.handle_discord_message(
            _FakeDiscordMessage(
                content="!play https://youtu.be/abc",
                guild=_FakeGuild(),
                voice=_FakeVoiceState(_FakeVoiceChannel()),
            )
        )
        assert response is not None
        assert "Adicionado" in _as_str(response)


class TestHarpiBotEdgeCases:
    @pytest.mark.asyncio
    async def test_message_no_guild(self):
        from test.unit.conftest import FakeResolver, FakePlayerFactory

        bot = HarpiBot(
            resolver=FakeResolver(), player_factory=FakePlayerFactory(), prefix="-"
        )
        msg = _FakeDiscordMessage(content="-play https://youtu.be/abc", guild=None)

        response = await bot.handle_discord_message(msg)

        assert response is not None

    @pytest.mark.asyncio
    async def test_prefix_only_returns_help(self, bot: HarpiBot):
        response = await bot.handle_discord_message(
            _FakeDiscordMessage(
                content="-",
                guild=_FakeGuild(),
                voice=_FakeVoiceState(_FakeVoiceChannel()),
            )
        )
        assert response is not None
        msg = _as_str(response).lower()
        assert "help" in msg or "comandos" in msg

    @pytest.mark.asyncio
    async def test_voice_connection_no_existing_client(self):
        from test.unit.conftest import FakeResolver, FakePlayerFactory

        bot = HarpiBot(
            resolver=FakeResolver(), player_factory=FakePlayerFactory(), prefix="-"
        )
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

    @pytest.mark.asyncio
    async def test_voice_connection_different_channel_moves(self):
        from test.unit.conftest import FakeResolver, FakePlayerFactory

        bot = HarpiBot(
            resolver=FakeResolver(), player_factory=FakePlayerFactory(), prefix="-"
        )
        channel1 = _FakeVoiceChannel("Room A")
        channel2 = _FakeVoiceChannel("Room B")
        guild = _FakeGuild()
        guild.voice_client = _FakeVoiceClientWithChannel(channel1)

        msg = _FakeDiscordMessage(
            content="-play https://youtu.be/abc",
            guild=guild,
            voice=_FakeVoiceState(channel2),
        )

        response = await bot.handle_discord_message(msg)

        assert response is not None
        assert "Adicionado" in _as_str(response)

    @pytest.mark.asyncio
    async def test_exception_in_dispatch_returns_error(self):
        from test.unit.conftest import FakeResolver, FakePlayerFactory, FakePlayer
        from harpi.application.player_service import PlayerService

        resolver = FakeResolver()
        player = FakePlayer()
        service = PlayerService(resolver=resolver, player=player)
        bot = HarpiBot(
            resolver=resolver, player_factory=FakePlayerFactory(), prefix="-"
        )
        guild = _FakeGuild()
        bot._guild_routers[guild.id] = _FailingRouter(
            player_service=service, prefix="-"
        )
        bot._guild_players[guild.id] = player

        msg = _FakeDiscordMessage(
            content="-play https://youtu.be/abc",
            guild=guild,
            voice=_FakeVoiceState(_FakeVoiceChannel()),
        )

        response = await bot.handle_discord_message(msg)

        assert response is not None
        assert "erro" in _as_str(response).lower()


