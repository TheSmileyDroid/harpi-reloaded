from harpi.application.ports.audio import AudioPlayerProtocol, AudioResolverProtocol
from harpi.domain.queue import Queue
from harpi.domain.track import Track


class PlayerService:
    def __init__(self, resolver: AudioResolverProtocol, player: AudioPlayerProtocol):
        self._queue: Queue = Queue()
        self._resolver: AudioResolverProtocol = resolver
        self._player: AudioPlayerProtocol = player

    @property
    def queue(self) -> Queue:
        return self._queue

    @property
    def playing(self) -> Track | None:
        return self._player.playing

    @property
    def position(self) -> float | None:
        return self._player.position

    @property
    def is_paused(self) -> bool:
        return self._player.is_paused

    async def play(self, link: str) -> None:
        track = await self._resolver.resolve(link)
        self._queue.add_track(track)
        if self._player.playing is None:
            await self._player.play(track, on_finish=self.on_track_end)

    async def on_track_end(self) -> None:
        self._queue.skip_track()
        next_track = self._queue.get_current_track()
        if next_track is not None:
            await self._player.play(next_track, on_finish=self.on_track_end)

    async def pause(self) -> None:
        await self._player.pause()

    async def resume(self) -> None:
        await self._player.resume()

    async def skip(self) -> None:
        await self._player.stop()
        await self.on_track_end()

    async def stop(self) -> None:
        self._queue.clear()
        await self._player.stop()
