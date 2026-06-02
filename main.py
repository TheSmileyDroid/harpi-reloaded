import asyncio
import os

import discord
from dotenv import load_dotenv

from harpi.application.player_service import PlayerService
from harpi.infrastructure.discord_bot import HarpiBot
from harpi.infrastructure.youtube_resolver import YoutubeResolver
from test.unit.conftest import FakePlayer


intents = discord.Intents.default()
intents.message_content = True


async def main():
    load_dotenv()

    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("Erro: Defina DISCORD_TOKEN no arquivo .env")
        return

    prefix = os.environ.get("BOT_PREFIX", "-")

    resolver = YoutubeResolver()
    player = FakePlayer()
    service = PlayerService(resolver=resolver, player=player)
    bot = HarpiBot(player_service=service, prefix=prefix)

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"Harpi conectado como {client.user}")

    @client.event
    async def on_message(message: discord.Message):
        if message.author.bot:
            return

        response = await bot.on_message(message.content, author_is_bot=False)
        if response is not None:
            await message.channel.send(response)

    await client.start(token)


if __name__ == "__main__":
    asyncio.run(main())
