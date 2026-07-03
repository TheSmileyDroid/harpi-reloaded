from harpi.application.commands import register
from harpi.application.player_service import PlayerService


@register("bg", guild_only=True, voice=True)
async def handle_bg(service: PlayerService, args: str) -> str:
    links = args.strip().split()
    if not links:
        return "Especifique ao menos uma URL ou termo de busca."
    succeeded, failed = await service.set_background_tracks(links)
    msg = f"Músicas de fundo substituídas: {succeeded} adicionadas."
    if failed:
        msg += f" {failed} falha(s) ignorada(s)."
    return msg
