from harpi.application.commands import register
from harpi.application.player_service import PlayerService


@register("resume", guild_only=True, voice=True)
async def handle_resume(service: PlayerService, args: str) -> str:
    await service.resume()
    return "Música retomada."
