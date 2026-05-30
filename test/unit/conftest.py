import pytest
from harpi.domain.track import Track, Source
from harpi.application.ports.audio import AudioPlayerProtocol, AudioResolverProtocol


class FakeResolver(AudioResolverProtocol):
    async def resolve(self, link: str) -> Track:
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

    @property
    def playing(self):
        return self._playing

    def play(self, track: Track):
        self._playing = track
        self.is_stopped = False
        self.is_paused = False

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def stop(self):
        self._playing = None
        self.is_stopped = True


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
