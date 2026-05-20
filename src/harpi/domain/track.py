from uuid import UUID
from uuid import uuid4
from functools import cached_property

from enum import Enum
from pydantic import BaseModel, Field, computed_field


class Source(Enum):
    YOUTUBE = "youtube"
    SPOTIFY = "spotify"


class Track(BaseModel):
    id: UUID = Field(
        default_factory=uuid4, description="The unique identifier for the track."
    )
    link: str = Field(..., description="The link to the track.", frozen=True)
    source: Source = Field(..., description="The source of the track.", frozen=True)
    title: str | None = Field(None, description="The title of the track.")
    duration: int | None = Field(
        None, description="The duration of the track in seconds."
    )
    resolved: bool = Field(
        False, description="Whether the track's info have been resolved."
    )

    @computed_field
    @cached_property
    def source_id(self) -> str:
        """Extract the source ID from the link."""
        if self.source == Source.YOUTUBE:
            if "youtu.be" in self.link:
                return self.link.split("/")[-1].split("?")[0]
            elif "youtube.com" in self.link:
                return self.link.split("v=")[-1].split("&")[0]
        elif self.source == Source.SPOTIFY:
            return self.link.split("/")[-1].split("?")[0]
        return ""

    def __eq__(self, other):
        if not isinstance(other, Track):
            return NotImplemented
        return self.source_id == other.source_id and self.source == other.source
