from dataclasses import dataclass, field

from harpi.domain.background_track_id import BackgroundTrackId
from harpi.domain.loop_mode import LoopMode
from harpi.domain.track_metadata import TrackMetadata


@dataclass(frozen=True, eq=False)
class BackgroundEntry:
    id: BackgroundTrackId
    metadata: TrackMetadata
    loop_mode: LoopMode = field(default_factory=lambda: LoopMode.OFF)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BackgroundEntry):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


class Background:
    def __init__(self):
        self._entries: list[BackgroundEntry] = []

    def add_entry(self, entry: BackgroundEntry) -> None:
        self._entries.append(entry)

    def remove_entry(self, bt_id: BackgroundTrackId) -> BackgroundEntry:
        for i, entry in enumerate(self._entries):
            if entry.id == bt_id:
                return self._entries.pop(i)
        raise KeyError(f"BackgroundTrackId {bt_id} not found")

    def get_entry(self, bt_id: BackgroundTrackId) -> BackgroundEntry | None:
        for entry in self._entries:
            if entry.id == bt_id:
                return entry
        return None

    def clear(self) -> None:
        self._entries.clear()

    @property
    def entries(self) -> list[BackgroundEntry]:
        return list(self._entries)
