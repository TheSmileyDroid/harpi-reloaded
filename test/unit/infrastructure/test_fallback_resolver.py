import pytest

from harpi.application.exceptions import InvalidLinkError, NetworkError
from harpi.domain.track_metadata import TrackMetadata, Source
from harpi.infrastructure.fallback_resolver import FallbackResolver


class FakeResolver:
    """Simple fake resolver for testing FallbackResolver."""

    def __init__(self, name: str = ""):
        self.name = name
        self._failures: dict[str, Exception] = {}

    async def resolve(self, link: str) -> TrackMetadata:
        if link in self._failures:
            raise self._failures[link]
        return TrackMetadata(
            link=link,
            source=Source.YOUTUBE,
            title=f"From {self.name}" if self.name else "Fake Track",
            duration=120,
        )

    async def resolve_stream(self, track: TrackMetadata) -> str:
        if track.link in self._failures:
            raise self._failures[track.link]
        return (
            f"stream://{self.name}/{track.link}"
            if self.name
            else f"stream://{track.link}"
        )

    def set_failure(self, link: str, exc: Exception) -> None:
        self._failures[link] = exc


class TestFallbackResolverInit:
    def test_empty_resolvers_raises(self):
        with pytest.raises(ValueError, match="At least one resolver"):
            FallbackResolver([])

    def test_single_resolver(self):
        r = FallbackResolver([FakeResolver("a")])
        assert len(r._resolvers) == 1

    def test_multiple_resolvers(self):
        r = FallbackResolver([FakeResolver("a"), FakeResolver("b")])
        assert len(r._resolvers) == 2


class TestFallbackResolverResolve:
    async def test_first_succeeds(self):
        r1 = FakeResolver("primary")
        r2 = FakeResolver("fallback")
        fb = FallbackResolver([r1, r2])

        result = await fb.resolve("https://youtu.be/abc")

        assert result.title == "From primary"

    async def test_first_fails_second_succeeds(self):
        r1 = FakeResolver("primary")
        r2 = FakeResolver("fallback")
        r1.set_failure("https://youtu.be/abc", InvalidLinkError("Not found"))
        fb = FallbackResolver([r1, r2])

        result = await fb.resolve("https://youtu.be/abc")

        assert result.title == "From fallback"

    async def test_all_fail_raises_last_error(self):
        r1 = FakeResolver("primary")
        r2 = FakeResolver("fallback")
        r1.set_failure("https://youtu.be/abc", InvalidLinkError("Not found"))
        r2.set_failure("https://youtu.be/abc", NetworkError("Network down"))
        fb = FallbackResolver([r1, r2])

        with pytest.raises(NetworkError, match="Network down"):
            await fb.resolve("https://youtu.be/abc")

    async def test_first_fails_no_second_fallback_still_works(self):
        r1 = FakeResolver("only")
        fb = FallbackResolver([r1])

        result = await fb.resolve("https://youtu.be/abc")

        assert result.title == "From only"

    async def test_first_fails_single_resolver_raises(self):
        r1 = FakeResolver("only")
        r1.set_failure("https://youtu.be/abc", InvalidLinkError("Bad"))
        fb = FallbackResolver([r1])

        with pytest.raises(InvalidLinkError):
            await fb.resolve("https://youtu.be/abc")


class TestAdaptiveFallback:
    """Tests that FallbackResolver dynamically reorders based on error counts."""

    async def test_error_count_increments_on_failure(self):
        r1 = FakeResolver("a")
        r2 = FakeResolver("b")
        r1.set_failure("https://youtu.be/abc", InvalidLinkError("Bad"))
        fb = FallbackResolver([r1, r2])

        result = await fb.resolve("https://youtu.be/abc")

        assert result.title == "From b"
        assert fb._error_counts.get(id(r1), 0) == 1
        assert fb._error_counts.get(id(r2), 0) == 0

    async def test_reorders_after_errors(self):
        """After r1 gets errors, r2 (0 errors) should be tried first."""
        r1 = FakeResolver("a")
        r2 = FakeResolver("b")
        r1.set_failure("https://youtu.be/abc", InvalidLinkError("Bad"))
        fb = FallbackResolver([r1, r2])

        await fb.resolve("https://youtu.be/abc")

        # Second call: r2 has 0 errors, should be tried first
        result = await fb.resolve("https://youtu.be/abc")
        assert result.title == "From b"

    async def test_fewer_errors_wins_even_when_second_in_list(self):
        """The resolver with fewer errors is tried first regardless of
        constructor order."""
        r1 = FakeResolver("error_prone")
        r2 = FakeResolver("reliable")
        r1.set_failure("https://youtu.be/abc", InvalidLinkError("Bad"))
        r1.set_failure("https://youtu.be/xyz", InvalidLinkError("Bad"))
        fb = FallbackResolver([r1, r2])

        await fb.resolve("https://youtu.be/abc")

        # Second call: r2 has 0 errors -> tried first -> succeeds
        result = await fb.resolve("https://youtu.be/xyz")
        assert result.title == "From reliable"

    async def test_errors_tracked_independently_per_resolver(self):
        r1 = FakeResolver("a")
        r2 = FakeResolver("b")
        r3 = FakeResolver("c")
        r1.set_failure("https://youtu.be/x", InvalidLinkError("Bad"))
        r3.set_failure("https://youtu.be/x", InvalidLinkError("Bad"))
        fb = FallbackResolver([r1, r2, r3])

        await fb.resolve("https://youtu.be/x")

        assert fb._error_counts.get(id(r1)) == 1
        assert fb._error_counts.get(id(r2), 0) == 0
        assert fb._error_counts.get(id(r3), 0) == 0

    async def test_reset_on_all_failed(self):
        """When all resolvers fail, error counts reset so the first resolver
        gets another chance next time."""
        r1 = FakeResolver("a")
        r2 = FakeResolver("b")
        r1.set_failure("https://youtu.be/x", InvalidLinkError("Bad"))
        r2.set_failure("https://youtu.be/x", InvalidLinkError("Bad"))
        fb = FallbackResolver([r1, r2])

        with pytest.raises(InvalidLinkError):
            await fb.resolve("https://youtu.be/x")

        # All failed -> reset
        assert fb._error_counts == {}


class TestFallbackResolverResolveStream:
    async def test_first_succeeds(self):
        r1 = FakeResolver("primary")
        r2 = FakeResolver("fallback")
        fb = FallbackResolver([r1, r2])
        track = TrackMetadata(
            link="https://youtu.be/abc",
            title="Test",
            duration=120,
            source=Source.YOUTUBE,
        )

        result = await fb.resolve_stream(track)

        assert result == "stream://primary/https://youtu.be/abc"

    async def test_first_fails_second_succeeds(self):
        r1 = FakeResolver("primary")
        r2 = FakeResolver("fallback")
        r1.set_failure("https://youtu.be/abc", InvalidLinkError("Not found"))
        fb = FallbackResolver([r1, r2])
        track = TrackMetadata(
            link="https://youtu.be/abc",
            title="Test",
            duration=120,
            source=Source.YOUTUBE,
        )

        result = await fb.resolve_stream(track)

        assert result == "stream://fallback/https://youtu.be/abc"

    async def test_all_fail_raises_last_error(self):
        r1 = FakeResolver("primary")
        r2 = FakeResolver("fallback")
        r1.set_failure("https://youtu.be/abc", InvalidLinkError("Not found"))
        r2.set_failure("https://youtu.be/abc", NetworkError("Network down"))
        fb = FallbackResolver([r1, r2])
        track = TrackMetadata(
            link="https://youtu.be/abc",
            title="Test",
            duration=120,
            source=Source.YOUTUBE,
        )

        with pytest.raises(NetworkError, match="Network down"):
            await fb.resolve_stream(track)


class TestFallbackErrorLogging:
    """Tests that all resolver errors are recorded and the last wins."""

    async def test_errors_are_collected_and_reset_on_all_fail_resolve(self):
        """After all resolvers fail, error counts reset for fairness."""
        r1 = FakeResolver("a")
        r2 = FakeResolver("b")
        r1.set_failure("https://youtu.be/x", InvalidLinkError("Bad1"))
        r2.set_failure("https://youtu.be/x", NetworkError("Bad2"))
        fb = FallbackResolver([r1, r2])

        with pytest.raises(Exception):
            await fb.resolve("https://youtu.be/x")

        # reset clears counts after all fail
        assert fb._error_counts == {}

    async def test_errors_are_collected_and_reset_on_all_fail_stream(self):
        r1 = FakeResolver("a")
        r2 = FakeResolver("b")
        r1.set_failure("https://youtu.be/x", InvalidLinkError("Bad1"))
        r2.set_failure("https://youtu.be/x", NetworkError("Bad2"))
        fb = FallbackResolver([r1, r2])
        track = TrackMetadata(
            link="https://youtu.be/x",
            title="T",
            duration=10,
            source=Source.YOUTUBE,
        )

        with pytest.raises(Exception):
            await fb.resolve_stream(track)

        assert fb._error_counts == {}

    async def test_resolve_passes_correct_error(self):
        """When all fail, the last resolver's error should be raised."""
        r1 = FakeResolver("a")
        r2 = FakeResolver("b")
        r1.set_failure("https://youtu.be/x", InvalidLinkError("First fail"))
        r2.set_failure("https://youtu.be/x", NetworkError("Last fail"))
        fb = FallbackResolver([r1, r2])

        with pytest.raises(NetworkError, match="Last fail"):
            await fb.resolve("https://youtu.be/x")

    async def test_stream_passes_correct_error(self):
        r1 = FakeResolver("a")
        r2 = FakeResolver("b")
        r1.set_failure("https://youtu.be/x", InvalidLinkError("First fail"))
        r2.set_failure("https://youtu.be/x", NetworkError("Last fail"))
        fb = FallbackResolver([r1, r2])
        track = TrackMetadata(
            link="https://youtu.be/x",
            title="T",
            duration=10,
            source=Source.YOUTUBE,
        )

        with pytest.raises(NetworkError, match="Last fail"):
            await fb.resolve_stream(track)
