from harpi.application.commands import register
from harpi.application.player_service import PlayerService


@register(
    "bgrm",
    guild_only=True,
    voice=True,
    description="remove o som de fundo <n> mostrado no queue",
)
async def handle_bgrm(service: PlayerService, args: str) -> str:
    index_str = args.strip()
    if not index_str:
        return "Especifique o índice da música de fundo."
    try:
        index = int(index_str)
    except ValueError:
        return "O índice deve ser um número."
    if index < 1:
        return f"Índice {index} inválido."
    try:
        # A lista do -queue numera os fundos a partir de 1.
        service.remove_background_track(index - 1)
        return f"Música de fundo {index} removida."
    except IndexError:
        return f"Índice {index} inválido."
