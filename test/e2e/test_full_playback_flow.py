import asyncio
import os
import pytest

from harpi.application.commands import EmbedData
from harpi.infrastructure.discord_bot import HarpiBot
from harpi.infrastructure.youtube_resolver import YoutubeResolver


pytestmark = pytest.mark.e2e


def _require_env() -> tuple[str, int, int]:
    token = os.environ.get("DISCORD_TOKEN")
    guild_id = os.environ.get("TEST_GUILD_ID")
    channel_id = os.environ.get("TEST_VOICE_CHANNEL_ID")
    if not token or not guild_id or not channel_id:
        pytest.skip("DISCORD_TOKEN, TEST_GUILD_ID, TEST_VOICE_CHANNEL_ID not set")
    return token, int(guild_id), int(channel_id)


class FakeAuthor:
    def __init__(self, bot: bool = False):
        self.bot = bot
        self.voice = None
        self.name = "TestUser"


class FakeVoiceState:
    def __init__(self, channel):
        self.channel = channel


class FakeMessage:
    def __init__(self, content: str, channel, guild, author: FakeAuthor):
        self.content = content
        self.channel = channel
        self.guild = guild
        self.author = author
        self._sent: list[str] = []

    async def reply(self, content: str) -> None:
        self._sent.append(content)

    @property
    def last_reply(self) -> str | None:
        return self._sent[-1] if self._sent else None


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def discord_client():
    import discord
    token, guild_id, channel_id = _require_env()
    intents = discord.Intents.default()
    intents.message_content = True
    intents.voice_states = True
    client = discord.Client(intents=intents)

    async def startup():
        await client.login(token)
        await client.connect()

    task = asyncio.create_task(startup())
    await asyncio.sleep(3)
    while not client.is_ready():
        await asyncio.sleep(0.5)

    yield client, guild_id, channel_id

    await client.close()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.fixture(scope="function")
async def test_guild(discord_client):
    client, guild_id, _ = discord_client
    guild = client.get_guild(guild_id)
    yield guild


@pytest.fixture(scope="function")
async def test_voice_channel(discord_client):
    _, _, channel_id = discord_client
    client, _, _ = discord_client
    guild_id = None
    for g in client.guilds:
        ch = g.get_channel(channel_id)
        if ch is not None:
            guild_id = g.id
            break
    if guild_id is None:
        pytest.skip("Test voice channel not found")
    guild = client.get_guild(guild_id)
    channel = guild.get_channel(channel_id)
    yield channel


@pytest.fixture(scope="function")
async def running_bot(discord_client):
    client, guild_id, channel_id = discord_client
    resolver = YoutubeResolver()
    bot = HarpiBot(resolver=resolver)

    guild = client.get_guild(guild_id)
    channel = guild.get_channel(channel_id)

    message = FakeMessage(
        content="-play https://youtu.be/jNQXAC9IVRw",
        channel=channel,
        guild=guild,
        author=FakeAuthor(bot=False),
    )
    message.author.voice = FakeVoiceState(channel)

    yield bot, message

    vc = guild.voice_client
    if vc is not None:
        await vc.disconnect()


@pytest.mark.asyncio
class TestFullPlaybackJourney:
    async def test_user_plays_track_and_stops(self, running_bot):
        bot, message = running_bot

        response = await bot.handle_discord_message(message)
        assert response is not None

        if isinstance(response, EmbedData):
            assert "Add" in response.description or "adicion" in response.description.lower()
        else:
            assert "Add" in response or "adicion" in response.lower()

        guild = message.guild
        assert guild.voice_client is not None
        assert guild.voice_client.is_connected()

        await asyncio.sleep(3)
        assert guild.voice_client.is_playing()

        stop_msg = FakeMessage(
            content="-stop",
            channel=message.channel,
            guild=message.guild,
            author=FakeAuthor(bot=False),
        )
        stop_msg.author.voice = FakeVoiceState(
            message.author.voice.channel
        )
        stop_response = await bot.handle_discord_message(stop_msg)
        assert stop_response is not None

        if isinstance(stop_response, EmbedData):
            assert "par" in stop_response.description or "stop" in stop_response.description.lower()
        else:
            assert "par" in stop_response or "stop" in stop_response.lower()

        await asyncio.sleep(0.5)
        assert not guild.voice_client.is_playing()
