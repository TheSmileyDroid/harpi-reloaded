import logging
from collections.abc import Awaitable, Callable

from harpi.application.player_service import PlayerService
from harpi.application.commands import get_handlers, Response, CommandHandler

logger = logging.getLogger(__name__)


class CommandRouter:
    def __init__(self, player_service: PlayerService, prefix: str = "-"):
        self._prefix = prefix
        self._player_service = player_service
        self._handlers: dict[str, CommandHandler] = {}
        for name, handler in get_handlers().items():
            self._handlers[name] = handler
        logger.info(
            "Registered %d command handlers: %s",
            len(self._handlers),
            ", ".join(self._handlers),
        )

    def _wrap(self, handler: CommandHandler) -> Callable[[str], Awaitable[Response]]:
        async def wrapped(args: str) -> Response:
            return await handler.func(self._player_service, args)

        return wrapped

    async def dispatch(self, message: str) -> Response | None:
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
            logger.info("Unknown command: %s", cmd_name)
            return self._help()

        logger.debug("Dispatching command %s with args %r", cmd_name, args)
        try:
            return await handler.func(self._player_service, args)
        except Exception as e:
            logger.exception("Error executing command %s", cmd_name)
            return f"Erro: {e}"

    def needs_voice(self, cmd_name: str) -> bool:
        handler = self._handlers.get(cmd_name)
        return handler is not None and handler.voice

    def _help(self) -> str:
        cmds = ", ".join(f"{self._prefix}{c}" for c in self._handlers)
        return f"Comandos disponíveis: {cmds}. Exemplo: {self._prefix}play <url>"
