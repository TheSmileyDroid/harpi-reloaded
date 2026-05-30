from uuid import UUID
from uuid import uuid4
from functools import cached_property
from dataclasses import dataclass, field

from enum import Enum


class Source(Enum):
    YOUTUBE = "youtube"
    SPOTIFY = "spotify"


@dataclass(frozen=True, eq=False)
class Track:
    link: str
    source: Source
    id: UUID = field(default_factory=uuid4)
    title: str | None = None
    duration: int | None = None
    resolved: bool = False

    @cached_property
    def source_id(self) -> str:
        """Extract the source ID from the link."""
        if self.source == Source.YOUTUBE:
            if "youtu.be" in self.link:
                return self.link.split("/")[-1].split("?")[0]
            elif "youtube.com" in self.link:
                if "v=" in self.link:
                    return self.link.split("v=")[-1].split("&")[0]
                return self.link.split("/")[-1].split("?")[0]
        elif self.source == Source.SPOTIFY:
            return self.link.split("/")[-1].split("?")[0]
        return ""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Track):
            return NotImplemented
        return self.source_id == other.source_id and self.source == other.source

    def __hash__(self) -> int:
        return hash((self.source_id, self.source))
