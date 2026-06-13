import asyncio
import logging
import os
from datetime import datetime

import discord
from dotenv import load_dotenv

from harpi.application.commands import EmbedData
from harpi.infrastructure.discord_bot import HarpiBot
from harpi.infrastructure.youtube_resolver import YoutubeResolver

logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True

BOT_COLOR = 0x57F287


async def main():
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        logger.error("DISCORD_TOKEN not set in .env file")
        return

    prefix = os.environ.get("BOT_PREFIX", "-")
    logger.info("Starting Harpi bot with prefix %r", prefix)

    resolver = YoutubeResolver()
    bot = HarpiBot(resolver=resolver, prefix=prefix)

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        assert client.user is not None
        logger.info("Bot connected as %s on %d guilds", client.user, len(client.guilds))

    @client.event
    async def on_message(message: discord.Message):
        response = await bot.handle_discord_message(message)
        if response is None:
            return

        if isinstance(response, EmbedData):
            embed = discord.Embed(
                description=response.description,
                color=BOT_COLOR,
                timestamp=datetime.now(),
            )
            if response.footer:
                embed.set_footer(text=response.footer)
            await message.channel.send(embed=embed)
        else:
            await message.channel.send(response)

    logger.info("Connecting to Discord gateway...")
    await client.start(token)


if __name__ == "__main__":
    asyncio.run(main())
