from harpi.application.player_service import PlayerService
from harpi.infrastructure.command_router import CommandRouter


class HarpiBot:
    def __init__(self, player_service: PlayerService, prefix: str = "-"):
        self._router = CommandRouter(player_service=player_service, prefix=prefix)

    async def on_message(self, content: str, author_is_bot: bool) -> str | None:
        if author_is_bot:
            return None

        return await self._router.dispatch(content)
