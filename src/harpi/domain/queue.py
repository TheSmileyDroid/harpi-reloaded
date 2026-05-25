from harpi.domain.track import Track
from enum import Enum


class LoopMode(Enum):
    TRACK = "track"
    QUEUE = "queue"
    OFF = "off"


class Queue:
    def __init__(self):
        self._queue: list[Track] = []
        self._background: list[Track] = []
        self._loop_mode: LoopMode = LoopMode.OFF

    def add_track(self, track: Track | list[Track]) -> None:
        if isinstance(track, list):
            self._queue.extend(track)
        else:
            self._queue.append(track)

    def clear_tracks(self) -> None:
        self._queue.clear()

    def set_background_tracks(self, tracks: list[Track]) -> None:
        self._background: list[Track] = list(tracks)

    def clear_background_tracks(self) -> None:
        self._background.clear()

    def get_current_track(self) -> Track | None:
        return self._queue[0] if self._queue else None

    def skip_track(self) -> Track | None:
        if self._queue:
            if self._loop_mode == LoopMode.TRACK:
                track = self._queue[0]
                # TODO: Resets the track to the beginning
                return track
            if self._loop_mode == LoopMode.QUEUE:
                track = self._queue.pop(0)
                self._queue.append(track)
                return track
            track = self._queue.pop(0)
            return track
        return None

    @property
    def loop_mode(self) -> LoopMode:
        return self._loop_mode

    def set_loop_mode(self, mode: LoopMode) -> None:
        self._loop_mode = mode

    def remove_track(self, track: Track) -> None:
        self._queue = [t for t in self._queue if t != track]

    @property
    def tracks(self) -> list[Track]:
        return list(self._queue)

    @property
    def background_tracks(self) -> list[Track]:
        return list(self._background)

    def clear(self) -> None:
        self._queue.clear()
