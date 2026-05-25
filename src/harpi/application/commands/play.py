from dataclasses import dataclass
from harpi.application.ports.command import Command
from typing import Protocol


class PlayerServiceProtocol(Protocol):
    async def play(self, link: str) -> None: ...


@dataclass(frozen=True)
class PlayCommand(Command[str]):
    query: str


class PlayCommandHandler:
    def __init__(self, player_service: PlayerServiceProtocol):
        self._player_service = player_service

    async def handle(self, command: PlayCommand) -> str:
        query = command.query.strip()
        if not query:
            return "A URL ou termo de busca não pode estar vazio."

        await self._player_service.play(query)
        return f"Adicionado: {query}"
