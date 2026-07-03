from harpi.application.ports.audio import AudioResolverProtocol
from harpi.domain.track_metadata import TrackMetadata


class TrackFactory:
    """Creates TrackMetadata by resolving links via AudioResolverProtocol."""

    def __init__(self, resolver: AudioResolverProtocol) -> None:
        self._resolver = resolver

    async def create(self, link: str) -> TrackMetadata:
        """Resolve a link and return TrackMetadata."""
        return await self._resolver.resolve(link)
