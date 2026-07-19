import logging

from harpi.application.ports.audio import AudioResolverProtocol
from harpi.domain.track_metadata import TrackMetadata

logger = logging.getLogger(__name__)


class FallbackResolver(AudioResolverProtocol):
    """A resolver that tries multiple resolvers, falling through on failure.

    Dynamically orders resolvers by historical error count — the resolver with
    the fewest errors is tried first, making it self-healing when one resolver
    starts failing more frequently than another.
    """

    _MAX_ERRORS = 100  # prevent unbounded growth

    def __init__(self, resolvers: list[AudioResolverProtocol]):
        if not resolvers:
            raise ValueError("At least one resolver is required")
        self._resolvers = list(resolvers)
        self._error_counts: dict[int, int] = {}

    def _sorted(self) -> list[AudioResolverProtocol]:
        """Return resolvers sorted by error count ascending."""
        return sorted(
            self._resolvers,
            key=lambda r: self._error_counts.get(id(r), 0),
        )

    def _record_error(self, resolver: AudioResolverProtocol) -> None:
        rid = id(resolver)
        count = self._error_counts.get(rid, 0)
        if count < self._MAX_ERRORS:
            self._error_counts[rid] = count + 1

    def _reset_if_all_failed(self) -> None:
        """When every resolver has errored, reset counts so the first resolver
        gets another fair chance next time."""
        total = len(self._resolvers)
        if sum(self._error_counts.get(id(r), 0) for r in self._resolvers) >= total:
            self._error_counts.clear()

    async def resolve(self, link: str) -> TrackMetadata:
        ordered = self._sorted()
        last_error: Exception | None = None

        for resolver in ordered:
            try:
                result = await resolver.resolve(link)
                return result
            except Exception as e:
                logger.debug(
                    "Resolver %s failed for %s: %s",
                    resolver.__class__.__name__,
                    link,
                    e,
                )
                self._record_error(resolver)
                last_error = e

        self._reset_if_all_failed()
        assert last_error is not None
        raise last_error

    async def resolve_stream(self, track: TrackMetadata) -> str:
        ordered = self._sorted()
        last_error: Exception | None = None

        for resolver in ordered:
            try:
                result = await resolver.resolve_stream(track)
                return result
            except Exception as e:
                logger.debug(
                    "Resolver %s failed to stream %s: %s",
                    resolver.__class__.__name__,
                    track.link,
                    e,
                )
                self._record_error(resolver)
                last_error = e

        self._reset_if_all_failed()
        assert last_error is not None
        raise last_error
