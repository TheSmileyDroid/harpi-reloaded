from collections.abc import Awaitable, Callable

from harpi.application.player_service import PlayerService
from harpi.application.commands import get_handlers, Handler


class CommandRouter:
    def __init__(self, player_service: PlayerService, prefix: str = "-"):
        self._prefix = prefix
        self._player_service = player_service
        self._handlers: dict[str, Callable[[str], Awaitable[str]]] = {}
        for name, handler in get_handlers().items():
            self._handlers[name] = self._wrap(handler)

    def _wrap(self, handler: Handler) -> Callable[[str], Awaitable[str]]:
        async def wrapped(args: str) -> str:
            return await handler(self._player_service, args)
        return wrapped

    async def dispatch(self, message: str) -> str | None:
        if not message:
            return self._help()

        if not message.startswith(self._prefix):
            return None

        stripped = message[len(self._prefix) :].strip()
        if not stripped:
            return self._help()

        parts = stripped.split(maxsplit=1)
        cmd_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        handler = self._handlers.get(cmd_name)
        if handler is None:
            return self._help()

        try:
            return await handler(args)
        except Exception as e:
            return f"Erro: {e}"

    def _help(self) -> str:
        cmds = ", ".join(f"{self._prefix}{c}" for c in self._handlers)
        return f"Comandos disponíveis: {cmds}. Exemplo: {self._prefix}play <url>"
