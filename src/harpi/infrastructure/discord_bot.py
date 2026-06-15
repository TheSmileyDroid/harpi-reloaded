import logging

from harpi.application.player_service import PlayerService
from harpi.application.ports.audio import AudioResolverProtocol
from harpi.application.commands import EmbedData
from harpi.infrastructure.command_router import CommandRouter
from harpi.infrastructure.discord_player import DiscordPlayer

logger = logging.getLogger(__name__)


class HarpiBot:
    def __init__(
        self,
        player_service: PlayerService | None = None,
        resolver: AudioResolverProtocol | None = None,
        prefix: str = "-",
    ):
        self._prefix = prefix
        self._resolver = resolver
        self._guild_players: dict[int, DiscordPlayer] = {}
        self._guild_routers: dict[int, CommandRouter] = {}

        if player_service is not None:
            self._router = CommandRouter(player_service=player_service, prefix=prefix)
        else:
            self._router = None

    def _ensure_guild_state(self, guild_id: int) -> CommandRouter | None:
        if guild_id in self._guild_routers:
            return self._guild_routers[guild_id]
        if self._resolver is None:
            return None
        player = DiscordPlayer()
        service = PlayerService(resolver=self._resolver, player=player)
        router = CommandRouter(player_service=service, prefix=self._prefix)
        self._guild_players[guild_id] = player
        self._guild_routers[guild_id] = router
        logger.debug("Created guild state for guild %d", guild_id)
        return router

    async def on_message(
        self, content: str, author_is_bot: bool
    ) -> str | EmbedData | None:
        if author_is_bot or self._router is None:
            return None
        return await self._router.dispatch(content)

    async def _ensure_voice_connection(self, message) -> str | None:
        guild_id = message.guild.id if message.guild else 0
        player = self._guild_players.get(guild_id)
        if player is not None and player.is_connected:
            return None
        if not message.author.voice:
            return "Você precisa estar em um canal de voz."
        player = self._guild_players.get(guild_id)
        if player is None:
            return None
        channel = message.author.voice.channel
        existing = message.guild.voice_client
        if existing is not None:
            player.set_voice_client(existing)
            if existing.channel != channel:
                await existing.move_to(channel)
        else:
            logger.info(
                "Joining voice channel %s in guild %s",
                channel.name,
                message.guild,
            )
            await player.connect(channel)
        return None

    async def handle_discord_message(self, message) -> str | EmbedData | None:
        if message.author.bot:
            return None

        content = message.content
        if not content.startswith(self._prefix):
            return None

        guild_id = message.guild.id if message.guild else 0
        cmd = (
            content[len(self._prefix) :].split()[0].lower()
            if len(content) > len(self._prefix)
            else ""
        )

        router = self._ensure_guild_state(guild_id)
        if router is None:
            return None

        if cmd and router.needs_voice(cmd):
            error = await self._ensure_voice_connection(message)
            if error is not None:
                return error

        try:
            return await router.dispatch(content)
        except Exception:
            logger.exception(
                "Unhandled error processing message from %s", message.author
            )
            return "Ocorreu um erro interno."
