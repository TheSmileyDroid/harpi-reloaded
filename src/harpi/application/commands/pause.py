from dataclasses import dataclass
from typing import Protocol
from harpi.application.ports.command import Command


class PausePlayerServiceProtocol(Protocol):
    def pause(self) -> None: ...


@dataclass(frozen=True)
class PauseCommand(Command[str]):
    pass


class PauseCommandHandler:
    def __init__(self, player_service: PausePlayerServiceProtocol):
        self._player_service = player_service

    async def handle(self, command: PauseCommand) -> str:
        self._player_service.pause()
        return "Música pausada."
