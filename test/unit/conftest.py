import pytest
from collections.abc import Callable, Coroutine
from typing import Any
from harpi.domain.track import Track, Source
from harpi.application.ports.audio import AudioPlayerProtocol, AudioResolverProtocol


class FakeResolver(AudioResolverProtocol):
    def __init__(self):
        self._failures: dict[str, Exception] = {}

    def set_failure(self, link: str, exc: Exception) -> None:
        self._failures[link] = exc

    async def resolve(self, link: str) -> Track:
        if link in self._failures:
            raise self._failures[link]
        return Track(
            link=link,
            title="Fake Track",
            duration=120,
            source=Source.YOUTUBE,
            resolved=True,
        )


class FakePlayer(AudioPlayerProtocol):
    def __init__(self):
        self._playing: Track | None = None
        self.background_tracks: list[Track] = []
        self.is_paused: bool = False
        self.is_stopped: bool = False
        self.volume: float = 1.0
        self.background_volume: float = 0.5
        self.is_ducking: bool = False
        self._duck_level: float = 0.2
        self._saved_background_volume: float | None = None
        self.on_finish: Callable[[], Coroutine[Any, Any, None]] | None = None
        self._position: float | None = None

    @property
    def playing(self) -> Track | None:
        return self._playing

    @property
    def position(self) -> float | None:
        return self._position

    async def play(
        self,
        track: Track,
        on_finish: Callable[[], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        self._playing = track
        self.is_stopped = False
        self.is_paused = False
        self.on_finish = on_finish

    async def pause(self) -> None:
        self.is_paused = True

    async def resume(self) -> None:
        self.is_paused = False

    async def stop(self) -> None:
        self._playing = None
        self.is_stopped = True

    def set_volume(self, volume: float) -> None:
        if not 0.0 <= volume <= 1.0:
            raise ValueError(f"Volume must be between 0.0 and 1.0, got {volume}")
        self.volume = volume

    def set_background_volume(self, volume: float) -> None:
        if not 0.0 <= volume <= 1.0:
            raise ValueError(
                f"Background volume must be between 0.0 and 1.0, got {volume}"
            )
        self.background_volume = volume

    def set_ducking(self, duck_level: float) -> None:
        if not 0.0 <= duck_level <= 1.0:
            raise ValueError(
                f"Duck level must be between 0.0 and 1.0, got {duck_level}"
            )
        self._duck_level = duck_level

    async def duck(self) -> None:
        if self.is_ducking:
            return
        self._saved_background_volume = self.background_volume
        self.background_volume = self._duck_level
        self.is_ducking = True

    async def unduck(self) -> None:
        if not self.is_ducking:
            return
        if self._saved_background_volume is not None:
            self.background_volume = self._saved_background_volume
            self._saved_background_volume = None
        self.is_ducking = False

    async def add_background_source(self, track: Track) -> None:
        self.background_tracks.append(track)

    def remove_background_source(self, index: int) -> Track:
        return self.background_tracks.pop(index)


@pytest.fixture
def fake_resolver():
    return FakeResolver()


@pytest.fixture
def fake_player():
    return FakePlayer()


@pytest.fixture()
def track1():
    return Track(
        link="https://youtu.be/abc",
        title="LOFI BEATS TO STUDY TO 1H",
        duration=3600,
        source=Source.YOUTUBE,
    )


@pytest.fixture()
def track2():
    return Track(
        link="https://youtu.be/def",
        title="ANOTHER LOFI BEAT",
        duration=1800,
        source=Source.YOUTUBE,
    )


@pytest.fixture()
def track3():
    return Track(
        link="https://youtu.be/ghi",
        title="THIRD TRACK",
        duration=900,
        source=Source.YOUTUBE,
    )


@pytest.fixture()
def spotify_track():
    return Track(
        link="https://open.spotify.com/track/4WvbyZqjR4XWg45H",
        title="Spotify Track",
        duration=240,
        source=Source.SPOTIFY,
    )


class FakeMessage:
    def __init__(self, content: str, author_id: int = 1, bot: bool = False):
        self.content = content
        self.author = FakeUser(author_id, bot)
        self.channel = FakeChannel()
        self._sent: list[str] = []

    async def reply(self, content: str) -> None:
        self._sent.append(content)

    @property
    def last_reply(self) -> str | None:
        return self._sent[-1] if self._sent else None


class FakeUser:
    def __init__(self, id: int = 1, bot: bool = False):
        self.id = id
        self.bot = bot
        self.name = f"User{id}"


class FakeChannel:
    def __init__(self, id: int = 1):
        self.id = id
        self.name = f"channel{id}"
        self._sent: list[str] = []

    async def send(self, content: str) -> None:
        self._sent.append(content)

    @property
    def last_message(self) -> str | None:
        return self._sent[-1] if self._sent else None
