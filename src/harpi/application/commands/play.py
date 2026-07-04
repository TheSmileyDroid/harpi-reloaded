from harpi.application.commands import register
from harpi.application.player_service import PlayerService


@register(
    "play",
    guild_only=True,
    voice=True,
    description="toca ou adiciona uma música à fila",
)
async def handle_play(service: PlayerService, args: str) -> str:
    query = args.strip()
    if not query:
        return "A URL ou termo de busca não pode estar vazio."
    await service.play(query)
    return f"Adicionado: {query}"
