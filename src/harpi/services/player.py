from harpi.domain.queue import Queue


class PlayerService:
    def __init__(self, resolver, player):
        self._queue = Queue()
        self._resolver = resolver
        self._player = player

    @property
    def queue(self) -> Queue:
        return self._queue

    async def play(self, link: str) -> None:
        track = await self._resolver.resolve(link)
        self._queue.add_track(track)
        if self._player.playing is None:
            self._player.play(track)
