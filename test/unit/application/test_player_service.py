from test.unit.conftest import FakeResolver, FakePlayer
from harpi.domain.queue import LoopMode
from harpi.application.player_service import PlayerService
from harpi.application.exceptions import InvalidLinkError, NetworkError, TimeoutError
import pytest
from harpi.domain.track import Track


class TestPlayerServicePlay:
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


class TestPlayerServicePauseResume:
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
    async def test_pause_without_playing_does_not_crash(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        svc.pause()
        assert player.is_paused is True

    @pytest.mark.asyncio
    async def test_resume_without_pausing_does_not_crash(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.play("https://youtu.be/abc")
        svc.resume()
        assert player.is_paused is False


class TestPlayerServiceSkip:
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
    async def test_skip_with_single_track_clears_playing(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.play("https://youtu.be/abc")
        svc.skip()
        assert player.playing is None
        assert len(svc.queue.tracks) == 0

    @pytest.mark.asyncio
    async def test_skip_with_three_tracks_advances_exactly_one(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.play("https://youtu.be/a")
        await svc.play("https://youtu.be/b")
        await svc.play("https://youtu.be/c")
        svc.skip()
        assert player.playing is not None
        assert player.playing.link == "https://youtu.be/b"
        assert len(svc.queue.tracks) == 2

    @pytest.mark.asyncio
    async def test_skip_all_tracks_clears_playing(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.play("https://youtu.be/a")
        await svc.play("https://youtu.be/b")
        svc.skip()
        svc.skip()
        assert player.playing is None
        assert len(svc.queue.tracks) == 0


class TestPlayerServiceStop:
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
    async def test_stop_on_empty_queue(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        svc.stop()
        assert len(svc.queue.tracks) == 0
        assert player.is_stopped is True
        assert player.playing is None

    @pytest.mark.asyncio
    async def test_stop_then_play_resumes(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.play("https://youtu.be/abc")
        svc.stop()
        assert player.is_stopped is True
        await svc.play("https://youtu.be/def")
        assert player.is_stopped is False
        assert player.playing is not None
        assert len(svc.queue.tracks) == 1


class TestPlayerServiceOnTrackEnd:
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

    @pytest.mark.asyncio
    async def test_on_track_end_loop_queue_advances_circularly(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        svc.queue.set_loop_mode(LoopMode.QUEUE)
        await svc.play("https://youtu.be/a")
        await svc.play("https://youtu.be/b")
        svc.on_track_end()
        assert player.playing is not None
        assert player.playing.link == "https://youtu.be/b"
        svc.on_track_end()
        assert player.playing is not None
        assert player.playing.link == "https://youtu.be/a"

    @pytest.mark.asyncio
    async def test_on_track_end_loop_off_exhausts_queue(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        svc.queue.set_loop_mode(LoopMode.OFF)
        await svc.play("https://youtu.be/a")
        await svc.play("https://youtu.be/b")
        svc.on_track_end()
        assert player.playing is not None
        assert player.playing.link == "https://youtu.be/b"
        svc.on_track_end()
        assert len(svc.queue.tracks) == 0
        assert svc.queue.get_current_track() is None
        assert player.playing is not None
        assert player.playing.link == "https://youtu.be/b"


class TestPlayerServiceWithFailingResolver:
    @pytest.mark.asyncio
    async def test_play_invalid_link_raises(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        resolver.set_failure("https://youtu.be/bad", InvalidLinkError("Bad link"))

        with pytest.raises(InvalidLinkError):
            await svc.play("https://youtu.be/bad")

        assert len(svc.queue.tracks) == 0
        assert player.playing is None

    @pytest.mark.asyncio
    async def test_play_timeout_raises(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        resolver.set_failure("https://youtu.be/slow", TimeoutError("Timed out"))

        with pytest.raises(TimeoutError):
            await svc.play("https://youtu.be/slow")

        assert len(svc.queue.tracks) == 0
        assert player.playing is None

    @pytest.mark.asyncio
    async def test_play_network_error_raises(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        resolver.set_failure("https://youtu.be/down", NetworkError("Network down"))

        with pytest.raises(NetworkError):
            await svc.play("https://youtu.be/down")

        assert len(svc.queue.tracks) == 0
        assert player.playing is None
