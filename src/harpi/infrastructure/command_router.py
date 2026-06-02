from collections.abc import Callable, Coroutine
from typing import Any

from harpi.application.player_service import PlayerService
from harpi.application.commands.play import PlayCommand, PlayCommandHandler
from harpi.application.commands.pause import PauseCommand, PauseCommandHandler
from harpi.application.commands.skip import SkipCommand, SkipCommandHandler
from harpi.application.commands.stop import StopCommand, StopCommandHandler
from harpi.application.commands.resume import ResumeCommand, ResumeCommandHandler


class CommandRouter:
    def __init__(self, player_service: PlayerService, prefix: str = "-"):
        self._prefix = prefix
        self._handlers: dict[str, Callable[[str], Coroutine[Any, Any, str]]] = {
            "play": lambda args: PlayCommandHandler(player_service).handle(PlayCommand(query=args)),
            "pause": lambda _: PauseCommandHandler(player_service).handle(PauseCommand()),
            "skip": lambda _: SkipCommandHandler(player_service).handle(SkipCommand()),
            "stop": lambda _: StopCommandHandler(player_service).handle(StopCommand()),
            "resume": lambda _: ResumeCommandHandler(player_service).handle(ResumeCommand()),
        }

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
