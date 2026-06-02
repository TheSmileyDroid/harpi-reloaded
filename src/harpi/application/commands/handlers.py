from harpi.application.commands import register
from harpi.application.player_service import PlayerService


@register("play")
async def handle_play(service: PlayerService, args: str) -> str:
    query = args.strip()
    if not query:
        return "A URL ou termo de busca não pode estar vazio."
    await service.play(query)
    return f"Adicionado: {query}"


@register("pause")
async def handle_pause(service: PlayerService, args: str) -> str:
    await service.pause()
    return "Música pausada."


@register("resume")
async def handle_resume(service: PlayerService, args: str) -> str:
    await service.resume()
    return "Música retomada."


@register("skip")
async def handle_skip(service: PlayerService, args: str) -> str:
    await service.skip()
    return "Música pulada."


@register("stop")
async def handle_stop(service: PlayerService, args: str) -> str:
    await service.stop()
    return "Fila limpa e música parada."


def _format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "--:--"
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"


def _format_queue(service: PlayerService) -> str:
    current = service.playing
    tracks = service.queue.tracks
    loop = service.queue.loop_mode.value

    if current is None:
        return f"Nada tocando no momento.\nFila: {len(tracks)} músicas | Loop: {loop}"

    lines: list[str] = []
    current_title = current.title or "Desconhecida"
    duration = _format_duration(current.duration)
    lines.append(f"▶ {current_title} ({duration})")
    for i, t in enumerate(tracks[1:], start=1):
        td = _format_duration(t.duration)
        title = t.title or "Desconhecida"
        lines.append(f"  {i}. {title} ({td})")
    lines.append(f"\nTotal: {len(tracks)} músicas | Loop: {loop}")
    return "\n".join(lines)


@register("queue")
async def handle_queue(service: PlayerService, args: str) -> str:
    return _format_queue(service)
