from harpi.application.ports.audio import AudioPlayerProtocol, AudioResolverProtocol
from harpi.domain.queue import Queue


class PlayerService:
    def __init__(self, resolver: AudioResolverProtocol, player: AudioPlayerProtocol):
        self._queue: Queue = Queue()
        self._resolver: AudioResolverProtocol = resolver
        self._player: AudioPlayerProtocol = player

    @property
    def queue(self) -> Queue:
        return self._queue

    async def play(self, link: str) -> None:
        track = await self._resolver.resolve(link)
        self._queue.add_track(track)
        if self._player.playing is None:
            self._player.play(track)

    def on_track_end(self) -> None:
        self._queue.skip_track()
        next_track = self._queue.get_current_track()
        if next_track is not None:
            self._player.play(next_track)

    def pause(self) -> None:
        self._player.pause()

    def resume(self) -> None:
        self._player.resume()

    def skip(self) -> None:
        self._player.stop()
        self.on_track_end()

    def stop(self) -> None:
        self._queue.clear()
        self._player.stop()
