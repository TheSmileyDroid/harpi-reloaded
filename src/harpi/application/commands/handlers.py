from harpi.application.commands import register, EmbedData, Response
from harpi.application.player_service import PlayerService
from harpi.domain.track import Track


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


@register("bg")
async def handle_bg(service: PlayerService, args: str) -> str:
    query = args.strip()
    if not query:
        return "A URL ou termo de busca não pode estar vazio."
    await service.add_background_track(query)
    return f"Música de fundo adicionada: {query}"


@register("bgrm")
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


def _format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "--:--"
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"


def _format_playing_duration(current: Track, position: float | None) -> str:
    duration = _format_duration(current.duration)
    if position is not None and current.duration is not None:
        pos = _format_duration(int(position))
        return f"{pos}/{duration}"
    return duration


def _build_queue_embed(service: PlayerService) -> str | EmbedData:
    current = service.playing
    tracks = service.queue.tracks
    bg_tracks = service.queue.background_tracks
    loop = service.queue.loop_mode.value
    total = len(tracks)
    footer_bg = f" | Fundo: {len(bg_tracks)}" if bg_tracks else ""

    if current is None:
        description = "Nada tocando no momento."
        if bg_tracks:
            bg_lines = ["", "**Músicas de fundo:**"]
            for i, t in enumerate(bg_tracks):
                td = _format_duration(t.duration)
                title = t.title or "Desconhecida"
                bg_lines.append(f"{i}. {title} ({td})")
            description = "\n".join([description] + bg_lines)
        return EmbedData(
            description=description,
            footer=f"Fila: {total} músicas{footer_bg} | Loop: {loop}",
        )

    duration = _format_playing_duration(current, service.position)
    current_title = current.title or "Desconhecida"
    lines = [f"{current_title} ({duration})"]

    for i, t in enumerate(tracks[1:], start=1):
        td = _format_duration(t.duration)
        title = t.title or "Desconhecida"
        lines.append(f"{i}. {title} ({td})")

    if bg_tracks:
        lines.append("")
        lines.append("**Músicas de fundo:**")
        for i, t in enumerate(bg_tracks):
            td = _format_duration(t.duration)
            title = t.title or "Desconhecida"
            lines.append(f"{i}. {title} ({td})")

    return EmbedData(
        description="\n".join(lines),
        footer=f"Total: {total} músicas{footer_bg} | Loop: {loop}",
    )


@register("queue")
async def handle_queue(service: PlayerService, args: str) -> Response:
    return _build_queue_embed(service)
