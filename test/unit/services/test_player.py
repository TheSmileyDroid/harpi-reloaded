from harpi.domain.track import Source
from harpi.services.player import PlayerService
import pytest
from harpi.domain.track import Track


class FakeResolver:
    async def resolve(self, link: str) -> Track:
        return Track(
            link=link,
            title="LOFI BEATS TO STUDY TO 1H",
            duration=3600,
            source=Source.YOUTUBE,
            resolved=True,
        )


class FakePlayer:
    def __init__(self):
        self.playing = None
        self.background_tracks = []

    def play(self, track: Track):
        self.playing = track

    def fake_end_current_track(self):
        if self.playing:
            self.playing = None


@pytest.fixture()
def track1():
    return Track(
        link="https://youtu.be/abc",
        title="LOFI BEATS TO STUDY TO 1H",
        duration=3600,
        source=Source.YOUTUBE,
    )


class TestPlayer:
    @pytest.mark.asyncio
    async def test_play_url_resolves_and_enqueues_track(self, track1: Track):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.play("https://youtu.be/abc")
        assert len(svc.queue.tracks) == 1
        assert svc.queue.get_current_track() == track1
        assert player.playing == track1
