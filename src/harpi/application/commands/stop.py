from dataclasses import dataclass
from harpi.application.ports.command import Command
from typing import Protocol


class StopPlayerServiceProtocol(Protocol):
    def stop(self) -> None: ...


@dataclass(frozen=True)
class StopCommand(Command[str]):
    pass


class StopCommandHandler:
    def __init__(self, player_service: StopPlayerServiceProtocol):
        self._player_service = player_service

    async def handle(self, command: StopCommand) -> str:
        self._player_service.stop()
        return "Fila limpa e música parada."
