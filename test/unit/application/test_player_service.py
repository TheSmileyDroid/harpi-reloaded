from harpi.application.ports.audio import AudioPlayerProtocol
from harpi.application.ports.audio import AudioResolverProtocol
from harpi.domain.queue import LoopMode
from harpi.domain.track import Source
from harpi.application.player_service import PlayerService
import pytest
from harpi.domain.track import Track


class FakeResolver(AudioResolverProtocol):
    async def resolve(self, link: str) -> Track:
        return Track(
            link=link,
            title="LOFI BEATS TO STUDY TO 1H",
            duration=3600,
            source=Source.YOUTUBE,
            resolved=True,
        )


class FakePlayer(AudioPlayerProtocol):
    def __init__(self):
        self._playing = None
        self.background_tracks = []
        self.is_paused = False
        self.is_stopped = False

    @property
    def playing(self):
        return self._playing

    def play(self, track: Track):
        self._playing = track
        self.is_stopped = False
        self.is_paused = False

    def pause(self) -> None:
        self.is_paused = True

    def resume(self) -> None:
        self.is_paused = False

    def stop(self) -> None:
        self._playing = None
        self.is_stopped = True


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

    @pytest.mark.asyncio
    async def test_play_enqueues_without_calling_play_when_already_playing(
        self, track1: Track
    ):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.play("https://youtu.be/abc")
        await svc.play("https://youtu.be/def")
        assert len(svc.queue.tracks) == 2
        assert player.playing == track1

    @pytest.mark.asyncio
    async def test_pause_and_resume_track(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)

        await svc.play("https://youtu.be/abc")
        assert not player.is_paused

        svc.pause()
        assert player.is_paused

        svc.resume()
        assert not player.is_paused

    @pytest.mark.asyncio
    async def test_skip_track_stops_current_and_starts_next(self, track2: Track):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)

        await svc.play("https://youtu.be/abc")
        await svc.play("https://youtu.be/def")  # track2

        svc.skip()

        assert player.is_stopped is False
        assert player.playing == track2

    @pytest.mark.asyncio
    async def test_stop_clears_queue_and_stops_playing(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)

        await svc.play("https://youtu.be/abc")
        await svc.play("https://youtu.be/def")

        svc.stop()

        assert len(svc.queue.tracks) == 0
        assert player.is_stopped is True
        assert player.playing is None

    @pytest.mark.asyncio
    async def test_on_track_end_advances_to_next_track(
        self, track1: Track, track2: Track
    ):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.play("https://youtu.be/abc")
        await svc.play("https://youtu.be/def")
        assert player.playing == track1
        svc.on_track_end()
        assert player.playing == track2

    @pytest.mark.asyncio
    async def test_on_track_end_with_single_track_does_not_replay(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.play("https://youtu.be/abc")
        svc.on_track_end()
        assert svc.queue.get_current_track() is None

    @pytest.mark.asyncio
    async def test_on_track_end_loop_track_replays_same(self, track1: Track):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        svc.queue.set_loop_mode(LoopMode.TRACK)
        await svc.play("https://youtu.be/abc")
        assert player.playing == track1
        svc.on_track_end()
        assert player.playing == track1

    @pytest.mark.asyncio
    async def test_on_track_end_empty_queue_does_nothing(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        svc.on_track_end()
        assert player.playing is None
