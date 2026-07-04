from harpi.application.commands import register
from harpi.application.player_service import PlayerService
from harpi.domain.loop_mode import LoopMode


@register(
    "loop",
    guild_only=True,
    voice=True,
    description="define o loop da fila: off, track ou queue",
)
async def handle_loop(service: PlayerService, args: str) -> str:
    mode_str = args.strip().lower()
    if not mode_str:
        current = service.queue.loop_mode
        modes = list(LoopMode)
        idx = modes.index(current)
        next_mode = modes[(idx + 1) % len(modes)]
        service.queue.set_loop_mode(next_mode)
        return f"Loop: {current.value} → {next_mode.value}"
    mode_map = {
        "off": LoopMode.OFF,
        "track": LoopMode.TRACK,
        "queue": LoopMode.QUEUE,
    }
    if mode_str not in mode_map:
        return "Modos válidos: off, track, queue."
    service.queue.set_loop_mode(mode_map[mode_str])
    return f"Loop definido para {mode_str}."
