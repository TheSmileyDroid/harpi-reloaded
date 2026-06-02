from collections.abc import Callable, Awaitable
from harpi.application.player_service import PlayerService

Handler = Callable[[PlayerService, str], Awaitable[str]]
_registry: dict[str, Handler] = {}


def register(name: str) -> Callable[[Handler], Handler]:
    def decorator(func: Handler) -> Handler:
        _registry[name] = func
        return func
    return decorator


def get_handlers() -> dict[str, Handler]:
    return dict(_registry)


from harpi.application.commands import handlers  # noqa: E402, F401
