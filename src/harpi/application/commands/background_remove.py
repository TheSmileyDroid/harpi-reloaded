from harpi.application.commands import register
from harpi.application.player_service import PlayerService


@register("bgrm", guild_only=True, voice=True)
async def handle_bgrm(service: PlayerService, args: str) -> str:
    index_str = args.strip()
    if not index_str:
        return "Especifique o índice da música de fundo."
    try:
        index = int(index_str)
    except ValueError:
        return "O índice deve ser um número."
    try:
        service.remove_background_track(index)
        return f"Música de fundo {index} removida."
    except IndexError:
        return f"Índice {index} inválido."
