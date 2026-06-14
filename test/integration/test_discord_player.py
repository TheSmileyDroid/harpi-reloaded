import asyncio
import os
import pytest

from harpi.domain.track import Track, Source
from harpi.infrastructure.discord_player import DiscordPlayer


pytestmark = pytest.mark.integration


def _require_env() -> tuple[str, int, int]:
    token = os.environ.get("DISCORD_TOKEN")
    guild_id = os.environ.get("TEST_GUILD_ID")
    channel_id = os.environ.get("TEST_VOICE_CHANNEL_ID")
    if not token or not guild_id or not channel_id:
        pytest.skip("DISCORD_TOKEN, TEST_GUILD_ID, TEST_VOICE_CHANNEL_ID not set")
    return token, int(guild_id), int(channel_id)


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

    import asyncio

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


@pytest.fixture(scope="session")
async def voice_client(discord_client):
    client, guild_id, channel_id = discord_client
    guild = client.get_guild(guild_id)
    channel = guild.get_channel(channel_id)
    vc = await channel.connect()
    yield vc
    await vc.disconnect()


@pytest.fixture
def test_track() -> Track:
    return Track(
        link="https://youtu.be/jNQXAC9IVRw",
        title="Me at the zoo",
        duration=19,
        source=Source.YOUTUBE,
        resolved=True,
    )


class TestDiscordPlayerRealVoice:
    @pytest.mark.asyncio
    async def test_play_real_audio_stream(self, voice_client, test_track):
        player = DiscordPlayer(voice_client=voice_client)
        await player.play(test_track)

        assert player.playing is not None
        assert player.playing.title == "Me at the zoo"
        assert not player.is_paused
        assert not player.is_stopped

        await asyncio.sleep(2)
        assert voice_client.is_playing()

        await player.stop()
        assert player.is_stopped
        assert player.playing is None

    @pytest.mark.asyncio
    async def test_pause_resume_real(self, voice_client, test_track):
        player = DiscordPlayer(voice_client=voice_client)
        await player.play(test_track)
        await asyncio.sleep(1)

        await player.pause()
        assert player.is_paused
        assert voice_client.is_paused()

        await player.resume()
        assert not player.is_paused
        assert voice_client.is_playing()

        await player.stop()

    @pytest.mark.asyncio
    async def test_position_updates_during_playback(self, voice_client, test_track):
        player = DiscordPlayer(voice_client=voice_client)
        await player.play(test_track)
        await asyncio.sleep(1.5)

        pos = player.position
        assert pos is not None
        assert pos >= 1.0

        await player.stop()

    @pytest.mark.asyncio
    async def test_on_finish_callback_fires(self, voice_client):
        player = DiscordPlayer(voice_client=voice_client)
        finished = asyncio.Event()

        async def on_finish():
            finished.set()

        track = Track(
            link="https://youtu.be/jNQXAC9IVRw",
            title="Me at the zoo",
            duration=19,
            source=Source.YOUTUBE,
            resolved=True,
        )
        await player.play(track, on_finish=on_finish)
        await asyncio.sleep(1)

        await player.stop()
        await asyncio.wait_for(finished.wait(), timeout=5.0)
