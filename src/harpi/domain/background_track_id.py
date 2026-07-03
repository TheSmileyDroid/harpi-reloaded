from uuid import UUID
from uuid import uuid4
from dataclasses import dataclass, field


@dataclass(frozen=True)
class BackgroundTrackId:
    """Value object wrapping UUID for background track identification."""

    value: UUID = field(default_factory=uuid4)

    def __str__(self) -> str:
        return str(self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BackgroundTrackId):
            return NotImplemented
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)
