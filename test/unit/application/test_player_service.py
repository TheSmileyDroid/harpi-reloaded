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
        assert player.on_finish == svc.on_track_end

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

        await svc.pause()

        assert player.is_paused

        await svc.resume()
        assert not player.is_paused

    @pytest.mark.asyncio
    async def test_pause_without_playing_does_not_crash(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.pause()
        assert player.is_paused is True

    @pytest.mark.asyncio
    async def test_resume_without_pausing_does_not_crash(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.play("https://youtu.be/abc")
        await svc.resume()
        assert player.is_paused is False


class TestPlayerServiceSkip:
    @pytest.mark.asyncio
    async def test_skip_track_stops_current_and_starts_next(self, track2: Track):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)

        await svc.play("https://youtu.be/abc")
        await svc.play("https://youtu.be/def")  # track2

        await svc.skip()

        assert player.is_stopped is False
        assert player.playing == track2

    @pytest.mark.asyncio
    async def test_skip_with_single_track_clears_playing(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.play("https://youtu.be/abc")
        await svc.skip()
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
        await svc.skip()
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
        await svc.skip()
        await svc.skip()
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

        await svc.stop()

        assert len(svc.queue.tracks) == 0
        assert player.is_stopped is True
        assert player.playing is None

    @pytest.mark.asyncio
    async def test_stop_on_empty_queue(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.stop()
        assert len(svc.queue.tracks) == 0
        assert player.is_stopped is True
        assert player.playing is None

    @pytest.mark.asyncio
    async def test_stop_then_play_resumes(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.play("https://youtu.be/abc")
        await svc.stop()
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
        await svc.on_track_end()
        assert player.playing == track2
        assert player.on_finish == svc.on_track_end

    @pytest.mark.asyncio
    async def test_on_track_end_with_single_track_does_not_replay(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.play("https://youtu.be/abc")
        await svc.on_track_end()
        assert svc.queue.get_current_track() is None

    @pytest.mark.asyncio
    async def test_on_track_end_loop_track_replays_same(self, track1: Track):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        svc.queue.set_loop_mode(LoopMode.TRACK)
        await svc.play("https://youtu.be/abc")
        assert player.playing == track1
        await svc.on_track_end()
        assert player.playing == track1

    @pytest.mark.asyncio
    async def test_on_track_end_empty_queue_does_nothing(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.on_track_end()
        assert player.playing is None

    @pytest.mark.asyncio
    async def test_on_track_end_loop_queue_advances_circularly(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        svc.queue.set_loop_mode(LoopMode.QUEUE)
        await svc.play("https://youtu.be/a")
        await svc.play("https://youtu.be/b")
        await svc.on_track_end()
        assert player.playing is not None
        assert player.playing.link == "https://youtu.be/b"
        await svc.on_track_end()
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
        await svc.on_track_end()
        assert player.playing is not None
        assert player.playing.link == "https://youtu.be/b"
        await svc.on_track_end()
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


class TestPlayerServiceBackgroundAdd:
    @pytest.mark.asyncio
    async def test_add_background_track_resolves_and_adds(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.add_background_track("https://youtu.be/abc")
        assert len(svc.queue.background_tracks) == 1
        assert svc.queue.background_tracks[0].link == "https://youtu.be/abc"

    @pytest.mark.asyncio
    async def test_add_background_track_does_not_affect_main_queue(self, track1: Track):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.play("https://youtu.be/abc")
        await svc.add_background_track("https://youtu.be/def")
        assert len(svc.queue.background_tracks) == 1
        assert len(svc.queue.tracks) == 1
        assert player.playing == track1

    @pytest.mark.asyncio
    async def test_add_background_track_failing_link_raises(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        resolver.set_failure("https://youtu.be/bad", InvalidLinkError("Bad link"))
        with pytest.raises(InvalidLinkError):
            await svc.add_background_track("https://youtu.be/bad")


class TestPlayerServiceBackgroundRemove:
    @pytest.mark.asyncio
    async def test_remove_background_track_by_index(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.add_background_track("https://youtu.be/abc")
        await svc.add_background_track("https://youtu.be/def")
        svc.remove_background_track(0)
        assert len(svc.queue.background_tracks) == 1
        assert svc.queue.background_tracks[0].link == "https://youtu.be/def"

    @pytest.mark.asyncio
    async def test_remove_background_track_out_of_bounds(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.add_background_track("https://youtu.be/abc")
        with pytest.raises(IndexError):
            svc.remove_background_track(5)


class TestPlayerServiceBackgroundSet:
    @pytest.mark.asyncio
    async def test_set_background_tracks_replaces_all(self, track1: Track):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.add_background_track("https://youtu.be/old")
        await svc.play("https://youtu.be/abc")
        succeeded, failed = await svc.set_background_tracks(
            ["https://youtu.be/x", "https://youtu.be/y"]
        )
        assert succeeded == 2
        assert failed == 0
        assert len(svc.queue.background_tracks) == 2
        assert len(svc.queue.tracks) == 1
        assert svc.queue.get_current_track() == track1

    @pytest.mark.asyncio
    async def test_set_background_tracks_partial_failure(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        resolver.set_failure("https://youtu.be/bad", InvalidLinkError("Bad link"))
        await svc.add_background_track("https://youtu.be/old")
        succeeded, failed = await svc.set_background_tracks(
            ["https://youtu.be/bad", "https://youtu.be/good"]
        )
        assert succeeded == 1
        assert failed == 1
        assert len(svc.queue.background_tracks) == 1

    @pytest.mark.asyncio
    async def test_set_background_tracks_all_fail_preserves_original(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.add_background_track("https://youtu.be/original")
        resolver.set_failure("https://youtu.be/bad1", InvalidLinkError("Bad"))
        resolver.set_failure("https://youtu.be/bad2", InvalidLinkError("Bad"))
        succeeded, failed = await svc.set_background_tracks(
            ["https://youtu.be/bad1", "https://youtu.be/bad2"]
        )
        assert succeeded == 0
        assert failed == 2
        assert len(svc.queue.background_tracks) == 1
        assert svc.queue.background_tracks[0].link == "https://youtu.be/original"


class TestPlayerServiceBackgroundIsolation:
    @pytest.mark.asyncio
    async def test_on_track_end_preserves_background(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.add_background_track("https://youtu.be/bg")
        await svc.play("https://youtu.be/abc")
        await svc.on_track_end()
        assert len(svc.queue.background_tracks) == 1
        assert svc.queue.background_tracks[0].link == "https://youtu.be/bg"


class TestPlayerServiceDucking:
    @pytest.mark.asyncio
    async def test_play_ducks_background_when_nothing_playing(self, track1: Track):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.play("https://youtu.be/abc")
        assert player.is_ducking is True
        assert player.background_volume == player._duck_level

    @pytest.mark.asyncio
    async def test_play_does_not_duck_again_when_already_playing(self, track1: Track):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.play("https://youtu.be/abc")
        assert player.is_ducking is True
        player.background_volume = 0.8
        await svc.play("https://youtu.be/def")
        assert player.is_ducking is True
        assert player.background_volume == 0.8

    @pytest.mark.asyncio
    async def test_on_track_end_unducks_when_queue_empty(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.play("https://youtu.be/abc")
        assert player.is_ducking is True
        await svc.on_track_end()
        assert player.is_ducking is False

    @pytest.mark.asyncio
    async def test_on_track_end_does_not_unduck_when_more_tracks(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.play("https://youtu.be/abc")
        await svc.play("https://youtu.be/def")
        await svc.on_track_end()
        assert player.is_ducking is True

    @pytest.mark.asyncio
    async def test_stop_unducks_background(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.play("https://youtu.be/abc")
        assert player.is_ducking is True
        await svc.stop()
        assert player.is_ducking is False

    @pytest.mark.asyncio
    async def test_stop_on_empty_queue_does_not_crash(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.stop()
        assert player.is_ducking is False

    @pytest.mark.asyncio
    async def test_skip_keeps_ducking_when_more_tracks(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.play("https://youtu.be/a")
        await svc.play("https://youtu.be/b")
        assert player.is_ducking is True
        await svc.skip()
        assert player.is_ducking is True

    @pytest.mark.asyncio
    async def test_skip_to_last_then_on_track_end_unducks(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        await svc.play("https://youtu.be/a")
        await svc.play("https://youtu.be/b")
        await svc.skip()
        assert player.is_ducking is True
        await svc.on_track_end()
        assert player.is_ducking is False


class TestPlayerServiceVolume:
    @pytest.mark.asyncio
    async def test_set_volume_delegates_to_player(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        svc.set_volume(0.5)
        assert player.volume == 0.5

    @pytest.mark.asyncio
    async def test_set_volume_minimum(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        svc.set_volume(0.0)
        assert player.volume == 0.0

    @pytest.mark.asyncio
    async def test_set_volume_maximum(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        svc.set_volume(1.0)
        assert player.volume == 1.0

    @pytest.mark.asyncio
    async def test_set_volume_below_minimum_raises(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        with pytest.raises(ValueError):
            svc.set_volume(-0.1)

    @pytest.mark.asyncio
    async def test_set_volume_above_maximum_raises(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        with pytest.raises(ValueError):
            svc.set_volume(1.1)

    @pytest.mark.asyncio
    async def test_set_background_volume_delegates_to_player(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        svc.set_background_volume(0.3)
        assert player.background_volume == 0.3

    @pytest.mark.asyncio
    async def test_set_background_volume_below_minimum_raises(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        with pytest.raises(ValueError):
            svc.set_background_volume(-0.1)

    @pytest.mark.asyncio
    async def test_set_background_volume_above_maximum_raises(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        with pytest.raises(ValueError):
            svc.set_background_volume(1.1)

    @pytest.mark.asyncio
    async def test_set_ducking_delegates_to_player(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        svc.set_ducking(0.1)
        assert player._duck_level == 0.1

    @pytest.mark.asyncio
    async def test_set_ducking_below_minimum_raises(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        with pytest.raises(ValueError):
            svc.set_ducking(-0.1)

    @pytest.mark.asyncio
    async def test_set_ducking_above_maximum_raises(self):
        resolver = FakeResolver()
        player = FakePlayer()
        svc = PlayerService(resolver=resolver, player=player)
        with pytest.raises(ValueError):
            svc.set_ducking(1.1)
