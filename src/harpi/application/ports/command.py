import typing

TResult = typing.TypeVar("TResult")


class Command(typing.Protocol[TResult]):
    pass


class CommandHandler(typing.Protocol[TResult]):
    async def handle(self, command: Command[TResult]) -> TResult: ...
