from collections.abc import Callable, Awaitable
from dataclasses import dataclass
from harpi.application.player_service import PlayerService


@dataclass
class EmbedData:
    title: str = ""
    description: str = ""
    footer: str = ""


@dataclass(frozen=True)
class CommandHandler:
    func: Callable[[PlayerService, str], Awaitable[str | EmbedData]]
    guild_only: bool = False
    voice: bool = False


Response = str | EmbedData
Handler = Callable[[PlayerService, str], Awaitable[Response]]
_registry: dict[str, CommandHandler] = {}


def register(
    name: str, guild_only: bool = False, voice: bool = False  # pragma: no mutate
) -> Callable[[Handler], Handler]:
    def decorator(func: Handler) -> Handler:
        _registry[name] = CommandHandler(func=func, guild_only=guild_only, voice=voice)
        return func

    return decorator


def get_handlers() -> dict[str, CommandHandler]:
    return dict(_registry)


from harpi.application.commands import handlers  # noqa: E402, F401
