from harpi.application.commands import register
from harpi.application.player_service import PlayerService


@register("rm", guild_only=True, voice=True)
async def handle_rm(service: PlayerService, args: str) -> str:
    index_str = args.strip()
    if not index_str:
        return "Especifique o índice da música."
    try:
        index = int(index_str)
    except ValueError:
        return "O índice deve ser um número."
    tracks = service.queue.tracks
    if index < 0 or index >= len(tracks):
        return f"Índice {index} inválido. Fila tem {len(tracks)} música(s)."
    removed = tracks[index]
    service.queue.remove_track(removed)
    title = removed.title or "Desconhecida"
    return f"Música removida: {title} (índice {index})."
