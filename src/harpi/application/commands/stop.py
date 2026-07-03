from harpi.application.commands import register
from harpi.application.player_service import PlayerService


@register("stop", guild_only=True, voice=True)
async def handle_stop(service: PlayerService, args: str) -> str:
    await service.stop()
    return "Fila limpa e música parada."
