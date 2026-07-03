from dataclasses import dataclass, field
from harpi.domain.queue import Queue
from harpi.domain.background import Background


@dataclass
class Guild:
    guild_id: int
    queue: Queue = field(default_factory=Queue)
    background: Background = field(default_factory=Background)
