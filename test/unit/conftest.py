from __future__ import annotations

import pytest
from collections.abc import Callable, Coroutine
from typing import Any

from harpi.domain.track_metadata import TrackMetadata, Source
from harpi.domain.volume import validate_volume
from harpi.application.ports.audio import AudioResolverProtocol, AudioPlayerProtocol


class FakeResolver(AudioResolverProtocol):
    def __init__(self) -> None:
        self._failures: dict[str, Exception] = {}

    async def resolve(self, link: str) -> TrackMetadata:
        if link in self._failures:
            raise self._failures[link]
        return TrackMetadata(
            link=link,
            source=Source.YOUTUBE,
            title="Fake Track",
            duration=120,
        )

    async def resolve_stream(self, track: TrackMetadata) -> str:
        return f"stream://{track.link}"

    def set_failure(self, link: str, exc: Exception) -> None:
        self._failures[link] = exc


class FakePlayer(AudioPlayerProtocol):
    def __init__(self) -> None:
        self._playing: TrackMetadata | None = None
        self._is_paused: bool = False
        self._is_stopped: bool = False
        self._background_tracks: list[TrackMetadata] = []
        self._on_finish: Callable[[], Coroutine[Any, Any, None]] | None = None
        self._volume: float = 1.0
        self._background_volume: float = 0.5
        self._is_ducking: bool = False
        self._duck_level: float = 0.1
        self._position: float | None = None

    @property
    def playing(self) -> TrackMetadata | None:
        return self._playing

    @property
    def position(self) -> float | None:
        return self._position

    @property
    def is_connected(self) -> bool:
        return True

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def is_stopped(self) -> bool:
        return self._is_stopped

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        self._volume = value

    @property
    def background_volume(self) -> float:
        return self._background_volume

    @background_volume.setter
    def background_volume(self, value: float) -> None:
        self._background_volume = value

    @property
    def is_ducking(self) -> bool:
        return self._is_ducking

    @property
    def background_tracks(self) -> list[TrackMetadata]:
        return self._background_tracks

    @property
    def on_finish(self) -> Callable[[], Coroutine[Any, Any, None]] | None:
        return self._on_finish

    async def play(
        self,
        track: TrackMetadata,
        on_finish: Callable[[], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        self._playing = track
        self._is_stopped = False
        self._is_paused = False
        self._on_finish = on_finish

    async def pause(self) -> None:
        self._is_paused = True

    async def resume(self) -> None:
        self._is_paused = False

    async def stop(self) -> None:
        self._is_stopped = True
        self._playing = None

    def set_volume(self, volume: float) -> None:
        validate_volume(volume)
        self._volume = volume

    def set_background_volume(self, volume: float) -> None:
        validate_volume(volume)
        self._background_volume = volume

    def set_ducking(self, duck_level: float) -> None:
        validate_volume(duck_level)
        self._duck_level = duck_level

    async def duck(self) -> None:
        self._is_ducking = True
        self._background_volume = self._duck_level

    async def unduck(self) -> None:
        self._is_ducking = False

    async def add_background_source(self, track: TrackMetadata) -> None:
        self._background_tracks.append(track)

    def remove_background_source(self, index: int) -> TrackMetadata:
        return self._background_tracks.pop(index)


@pytest.fixture
def track1() -> TrackMetadata:
    return TrackMetadata(
        link="https://youtu.be/abc",
        source=Source.YOUTUBE,
        title="Fake Track",
        duration=120,
    )


@pytest.fixture
def track2() -> TrackMetadata:
    return TrackMetadata(
        link="https://youtu.be/def",
        source=Source.YOUTUBE,
        title="Fake Track",
        duration=120,
    )


@pytest.fixture
def track3() -> TrackMetadata:
    return TrackMetadata(
        link="https://youtu.be/ghi",
        source=Source.YOUTUBE,
        title="Fake Track",
        duration=120,
    )
