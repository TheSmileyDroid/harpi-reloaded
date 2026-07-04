from harpi.application.commands import register
from harpi.application.player_service import PlayerService
from harpi.domain.volume import validate_volume


@register(
    "volume",
    guild_only=True,
    voice=True,
    description="define o volume da música, de 0.0 a 1.0",
)
async def handle_volume(service: PlayerService, args: str) -> str:
    level_str = args.strip()
    if not level_str:
        return "Especifique o nível de volume (0.0–1.0)."
    try:
        level = float(level_str)
    except ValueError:
        return "O nível de volume deve ser um número."
    try:
        validate_volume(level)
    except ValueError as e:
        return str(e)
    service.set_volume(level)
    return f"Volume definido para {level:.0%}."


@register(
    "bgvolume",
    guild_only=True,
    voice=True,
    description="define o volume dos sons de fundo, de 0.0 a 1.0",
)
async def handle_bgvolume(service: PlayerService, args: str) -> str:
    level_str = args.strip()
    if not level_str:
        return "Especifique o nível de volume de fundo (0.0–1.0)."
    try:
        level = float(level_str)
    except ValueError:
        return "O nível de volume deve ser um número."
    try:
        validate_volume(level)
    except ValueError as e:
        return str(e)
    service.set_background_volume(level)
    return f"Volume de fundo definido para {level:.0%}."


@register(
    "duck",
    guild_only=True,
    voice=True,
    description="define o quanto os fundos abaixam enquanto a música toca, de 0.0 a 1.0",
)
async def handle_duck(service: PlayerService, args: str) -> str:
    level_str = args.strip()
    if not level_str:
        return "Especifique o nível de ducking (0.0–1.0)."
    try:
        level = float(level_str)
    except ValueError:
        return "O nível de ducking deve ser um número."
    try:
        validate_volume(level)
    except ValueError as e:
        return str(e)
    service.set_ducking(level)
    return f"Nível de ducking definido para {level:.0%}."
