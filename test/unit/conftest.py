from __future__ import annotations

import pytest
from collections.abc import Callable, Coroutine
from typing import Any

from harpi.domain.track_metadata import TrackMetadata, Source
from harpi.domain.volume import validate_volume
from harpi.application.ports.audio import (
    AudioResolverProtocol,
    AudioPlayerProtocol,
    AudioPlayerFactoryProtocol,
)


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

    def get_last_stream_headers(self) -> dict[str, str]:
        return {}

    def get_last_stream_cookies(self) -> dict[str, str]:
        return {}

    def set_failure(self, link: str, exc: Exception) -> None:
        self._failures[link] = exc


class FakePlayer(AudioPlayerProtocol):
    def __init__(self) -> None:
        self._playing: TrackMetadata | None = None
        self.is_paused: bool = False
        self.background_tracks: list[TrackMetadata] = []
        self._on_finish: Callable[[], Coroutine[Any, Any, None]] | None = None
        self.volume: float = 1.0
        self.background_volume: float = 0.5
        self._duck_level: float = 0.1
        self._position: float | None = None
        self._is_connected: bool = False

    @property
    def playing(self) -> TrackMetadata | None:
        return self._playing

    @property
    def position(self) -> float | None:
        return self._position

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @property
    def on_finish(self) -> Callable[[], Coroutine[Any, Any, None]] | None:
        return self._on_finish

    async def play(
        self,
        track: TrackMetadata,
        on_finish: Callable[[], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        self._playing = track
        self.is_paused = False
        self._on_finish = on_finish

    async def pause(self) -> None:
        self.is_paused = True

    async def resume(self) -> None:
        self.is_paused = False

    async def stop(self) -> None:
        self._playing = None

    def set_volume(self, volume: float) -> None:
        validate_volume(volume)
        self.volume = volume

    def set_background_volume(self, volume: float) -> None:
        validate_volume(volume)
        self.background_volume = volume

    def set_ducking(self, duck_level: float) -> None:
        validate_volume(duck_level)
        self._duck_level = duck_level

    async def add_background_source(self, track: TrackMetadata) -> None:
        self.background_tracks.append(track)

    def remove_background_source(self, index: int) -> TrackMetadata:
        return self.background_tracks.pop(index)

    def set_voice_client(self, voice_client) -> None:
        pass

    async def connect(self, channel) -> None:
        self._is_connected = True


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


class FakePlayerFactory(AudioPlayerFactoryProtocol):
    def create_player(self, resolver: AudioResolverProtocol) -> AudioPlayerProtocol:
        return FakePlayer()


class FakeVoiceClient:
    def __init__(self):
        self._is_playing = False
        self._is_paused = False
        self._source = None
        self._after = None
        self.play_calls = 0

    def play(self, source, after=None):
        self._source = source
        self._after = after
        self._is_playing = True
        self._is_paused = False
        self.play_calls += 1

    def pause(self):
        self._is_paused = True
        self._is_playing = False

    def resume(self):
        self._is_paused = False
        self._is_playing = True

    def stop(self):
        self._is_playing = False
        self._is_paused = False
        if self._after is not None:
            after = self._after
            self._after = None
            after(None)

    def is_playing(self):
        return self._is_playing

    def is_paused(self):
        return self._is_paused


class DeferredAfterVoiceClient:
    """FakeVoiceClient that stores the `after` callback instead of firing it."""

    def __init__(self):
        self._is_playing = False
        self._is_paused = False
        self._source = None
        self._after = None
        self.play_calls = 0
        self._stored_afters: list = []

    def play(self, source, after=None):
        self._source = source
        self._after = after
        self._is_playing = True
        self._is_paused = False
        self.play_calls += 1

    def pause(self):
        self._is_paused = True
        self._is_playing = False

    def resume(self):
        self._is_paused = False
        self._is_playing = True

    def stop(self):
        self._is_playing = False
        self._is_paused = False
        if self._after is not None:
            self._stored_afters.append(self._after)
            self._after = None

    def fire_stored_after(self, index: int = -1) -> None:
        if self._stored_afters:
            after = self._stored_afters.pop(index)
            after(None)

    def fire_all_stored_afters(self) -> None:
        while self._stored_afters:
            after = self._stored_afters.pop(0)
            after(None)

    def is_playing(self):
        return self._is_playing

    def is_paused(self):
        return self._is_paused
