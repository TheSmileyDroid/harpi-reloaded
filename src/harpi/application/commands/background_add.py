from harpi.application.commands import register
from harpi.application.player_service import PlayerService


@register(
    "bgadd",
    guild_only=True,
    voice=True,
    description="adiciona um som de fundo, que toca em loop até ser removido",
)
async def handle_bgadd(service: PlayerService, args: str) -> str:
    query = args.strip()
    if not query:
        return "A URL ou termo de busca não pode estar vazio."
    await service.add_background_track(query)
    return f"Música de fundo adicionada: {query}"
