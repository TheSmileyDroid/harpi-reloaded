from dataclasses import dataclass
from harpi.application.ports.command import Command
from typing import Protocol


class SkipPlayerServiceProtocol(Protocol):
    async def skip(self) -> None: ...


@dataclass(frozen=True)
class SkipCommand(Command[str]):
    pass


class SkipCommandHandler:
    def __init__(self, player_service: SkipPlayerServiceProtocol):
        self._player_service = player_service

    async def handle(self, command: SkipCommand) -> str:
        await self._player_service.skip()
        return "Música pulada."
