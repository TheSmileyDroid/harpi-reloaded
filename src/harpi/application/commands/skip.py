from harpi.application.commands import register
from harpi.application.player_service import PlayerService


@register(
    "skip",
    guild_only=True,
    voice=True,
    description="pula para a próxima música da fila",
)
async def handle_skip(service: PlayerService, args: str) -> str:
    await service.skip()
    return "Música pulada."
