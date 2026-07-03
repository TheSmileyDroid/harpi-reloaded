from harpi.application.commands import register
from harpi.application.player_service import PlayerService


@register("skip", guild_only=True, voice=True)
async def handle_skip(service: PlayerService, args: str) -> str:
    await service.skip()
    return "Música pulada."
