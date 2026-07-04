from harpi.application.commands import register
from harpi.application.player_service import PlayerService


@register("pause", guild_only=True, voice=True, description="pausa a reprodução")
async def handle_pause(service: PlayerService, args: str) -> str:
    await service.pause()
    return "Música pausada."
