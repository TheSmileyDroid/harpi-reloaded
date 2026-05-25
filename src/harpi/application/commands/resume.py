from dataclasses import dataclass
from harpi.application.ports.command import Command
from typing import Protocol


class ResumePlayerServiceProtocol(Protocol):
    def resume(self) -> None: ...


@dataclass(frozen=True)
class ResumeCommand(Command[str]):
    pass


class ResumeCommandHandler:
    def __init__(self, player_service: ResumePlayerServiceProtocol):
        self._player_service = player_service

    async def handle(self, command: ResumeCommand) -> str:
        self._player_service.resume()
        return "Música retomada."
