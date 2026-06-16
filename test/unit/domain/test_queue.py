from harpi.domain.queue import LoopMode
import pytest
from harpi.domain.queue import Queue
from harpi.domain.track import Track, Source


@pytest.fixture()
def queue():
    return Queue()


@pytest.fixture()
def track1():
    return Track(source=Source.YOUTUBE, link="https://youtu.be/wPQEeBAXou0")


@pytest.fixture()
def track2():
    return Track(source=Source.YOUTUBE, link="https://youtu.be/7wtfhZwyrcc")


@pytest.fixture()
def track3():
    return Track(source=Source.YOUTUBE, link="https://youtu.be/cyzx45mupcQ")


class TestQueueAddTrack:
    def test_adds_track_to_queue(self, queue: Queue, track1: Track, track2: Track):
        queue.add_track(track1)
        assert len(queue.tracks) == 1
        assert queue.tracks[0] == track1

        queue.add_track(track2)
        assert len(queue.tracks) == 2
        assert queue.tracks[1] == track2

    def test_adds_multiple_tracks_to_queue(
        self, queue: Queue, track1: Track, track2: Track, track3: Track
    ):
        queue.add_track([track1, track2, track3])
        assert len(queue.tracks) == 3
        assert queue.tracks[0] == track1
        assert queue.tracks[1] == track2
        assert queue.tracks[2] == track3

    def test_add_track_empty_list(self, queue: Queue):
        queue.add_track([])
        assert len(queue.tracks) == 0

    def test_add_track_interleaved_with_skip(
        self, queue: Queue, track1: Track, track2: Track
    ):
        queue.add_track(track1)
        queue.skip_track()
        queue.add_track(track2)
        assert len(queue.tracks) == 1
        assert queue.get_current_track() == track2


class TestQueueGetCurrentTrack:
    def test_get_current_track(self, queue: Queue, track1: Track, track2: Track):
        queue.add_track(track1)
        queue.add_track(track2)
        assert queue.get_current_track() == track1

    def test_get_current_track_empty_queue(self, queue: Queue):
        assert queue.get_current_track() is None


class TestQueueClearTracks:
    def test_clears_tracks_from_queue(self, queue: Queue, track1: Track, track2: Track):
        queue.add_track([track1, track2])
        queue.clear_tracks()
        assert len(queue.tracks) == 0

    def test_clear_tracks_then_add(self, queue: Queue, track1: Track, track2: Track):
        queue.add_track([track1, track2])
        queue.clear_tracks()
        queue.add_track(track1)
        assert len(queue.tracks) == 1
        assert queue.get_current_track() == track1

    def test_clear_method_also_clears(self, queue: Queue, track1: Track):
        queue.add_track(track1)
        queue.clear()
        assert len(queue.tracks) == 0


class TestQueueBackgroundTracks:
    def test_adds_background_track(self, queue: Queue, track1: Track):
        queue.add_background_track(track1)
        assert len(queue.background_tracks) == 1
        assert queue.background_tracks[0] == track1

    def test_adds_multiple_background_tracks(
        self, queue: Queue, track1: Track, track2: Track
    ):
        queue.add_background_track(track1)
        queue.add_background_track(track2)
        assert len(queue.background_tracks) == 2
        assert queue.background_tracks[0] == track1
        assert queue.background_tracks[1] == track2

    def test_removes_background_track_by_index(
        self, queue: Queue, track1: Track, track2: Track
    ):
        queue.add_background_track(track1)
        queue.add_background_track(track2)
        queue.remove_background_track(0)
        assert len(queue.background_tracks) == 1
        assert queue.background_tracks[0] == track2

    def test_removes_background_track_by_index_out_of_bounds(
        self, queue: Queue, track1: Track
    ):
        queue.add_background_track(track1)
        with pytest.raises(IndexError):
            queue.remove_background_track(5)

    def test_removes_background_track_by_index_negative(self, queue: Queue):
        with pytest.raises(IndexError):
            queue.remove_background_track(-1)

    def test_removes_background_track_by_value(
        self, queue: Queue, track1: Track, track2: Track
    ):
        queue.add_background_track(track1)
        queue.add_background_track(track2)
        queue.remove_background_track(track1)
        assert len(queue.background_tracks) == 1
        assert queue.background_tracks[0] == track2

    def test_removes_background_track_by_value_not_found(
        self, queue: Queue, track1: Track, track2: Track
    ):
        queue.add_background_track(track1)
        queue.remove_background_track(track2)
        assert len(queue.background_tracks) == 1
        assert queue.background_tracks[0] == track1

    def test_clears_background_tracks(self, queue: Queue, track1: Track, track2: Track):
        queue.add_background_track(track1)
        queue.add_background_track(track2)
        queue.clear_background_tracks()
        assert len(queue.background_tracks) == 0

    def test_background_starts_empty(self, queue: Queue):
        assert len(queue.background_tracks) == 0
        assert queue.background_tracks == []

    def test_background_tracks_returns_copy(self, queue: Queue, track1: Track):
        queue.add_background_track(track1)
        bg = queue.background_tracks
        bg.clear()
        assert len(queue.background_tracks) == 1

    def test_next_background_track_empty(self, queue: Queue):
        assert queue.next_background_track() is None

    def test_next_background_track_loops(
        self, queue: Queue, track1: Track, track2: Track
    ):
        queue.add_background_track(track1)
        queue.add_background_track(track2)
        assert queue.next_background_track() is track1
        assert queue.next_background_track() is track2
        assert queue.next_background_track() is track1
        assert queue.next_background_track() is track2

    def test_set_background_tracks_replaces_all(
        self, queue: Queue, track1: Track, track2: Track, track3: Track
    ):
        queue.add_background_track(track1)
        queue.add_background_track(track2)
        queue.set_background_tracks([track3])
        assert len(queue.background_tracks) == 1
        assert queue.background_tracks[0] == track3

    def test_set_background_tracks_empty_clears(
        self, queue: Queue, track1: Track, track2: Track
    ):
        queue.add_background_track(track1)
        queue.add_background_track(track2)
        queue.set_background_tracks([])
        assert len(queue.background_tracks) == 0


class TestQueueDefensiveCopy:
    def test_tracks_returns_copy(self, queue: Queue, track1: Track, track2: Track):
        queue.add_track([track1, track2])
        tracks = queue.tracks
        tracks.clear()
        assert len(queue.tracks) == 2


class TestQueueSkipTrack:
    def test_skip_track(self, queue: Queue, track1: Track, track2: Track):
        queue.add_track([track1, track2])
        assert queue.get_current_track() == track1
        assert queue.skip_track() is track1
        assert queue.get_current_track() == track2
        assert queue.skip_track() is track2
        assert queue.get_current_track() is None

    def test_skip_track_empty_queue(self, queue: Queue):
        assert queue.skip_track() is None


class TestQueueLoopMode:
    def test_default_loop_mode_is_off(self, queue: Queue):
        assert queue.loop_mode == LoopMode.OFF

    def test_loop_mode_transitions(self, queue: Queue):
        assert queue.loop_mode == LoopMode.OFF
        queue.set_loop_mode(LoopMode.TRACK)
        assert queue.loop_mode == LoopMode.TRACK
        queue.set_loop_mode(LoopMode.QUEUE)
        assert queue.loop_mode == LoopMode.QUEUE
        queue.set_loop_mode(LoopMode.OFF)
        assert queue.loop_mode == LoopMode.OFF


class TestQueueLoopTrack:
    def test_loop_track_skips(self, queue: Queue, track1: Track):
        queue.set_loop_mode(LoopMode.TRACK)
        queue.add_track(track1)
        assert queue.skip_track() is track1
        assert queue.get_current_track() is track1

    def test_loop_track_does_not_advance_with_multiple_tracks(
        self, queue: Queue, track1: Track, track2: Track
    ):
        queue.set_loop_mode(LoopMode.TRACK)
        queue.add_track([track1, track2])
        queue.skip_track()
        assert queue.get_current_track() == track1
        assert len(queue.tracks) == 2

    def test_loop_track_on_empty_queue(self, queue: Queue):
        queue.set_loop_mode(LoopMode.TRACK)
        assert queue.skip_track() is None


class TestQueueLoopQueue:
    def test_loop_queue_skips(self, queue: Queue, track1: Track, track2: Track):
        queue.set_loop_mode(LoopMode.QUEUE)
        queue.add_track([track1, track2])
        assert queue.skip_track() is track1
        assert queue.get_current_track() == track2
        assert queue.skip_track() is track2
        assert queue.get_current_track() == track1

    def test_loop_queue_skips_single(self, queue: Queue, track1: Track):
        queue.set_loop_mode(LoopMode.QUEUE)
        queue.add_track(track1)
        assert queue.skip_track() is track1
        assert queue.get_current_track() is track1

    def test_loop_queue_on_empty_queue(self, queue: Queue):
        queue.set_loop_mode(LoopMode.QUEUE)
        assert queue.skip_track() is None

    def test_loop_queue_full_rotation(
        self, queue: Queue, track1: Track, track2: Track, track3: Track
    ):
        queue.set_loop_mode(LoopMode.QUEUE)
        queue.add_track([track1, track2, track3])
        queue.skip_track()
        queue.skip_track()
        queue.skip_track()
        assert queue.get_current_track() == track1
        assert len(queue.tracks) == 3


class TestQueueLoopOff:
    def test_loop_off_skips(self, queue: Queue, track1: Track, track2: Track):
        queue.set_loop_mode(LoopMode.OFF)
        queue.add_track([track1, track2])
        assert queue.skip_track() is track1
        assert queue.get_current_track() == track2
        assert queue.skip_track() is track2
        assert queue.get_current_track() is None


class TestQueueRemoveTrack:
    def test_remove_track_first(
        self, queue: Queue, track1: Track, track2: Track, track3: Track
    ):
        queue.add_track([track1, track2, track3])
        queue.remove_track(track1)
        assert len(queue.tracks) == 2
        assert queue.tracks[0] == track2

    def test_remove_track_last(
        self, queue: Queue, track1: Track, track2: Track, track3: Track
    ):
        queue.add_track([track1, track2, track3])
        queue.remove_track(track3)
        assert len(queue.tracks) == 2
        assert queue.tracks[-1] == track2

    def test_remove_track_middle(
        self, queue: Queue, track1: Track, track2: Track, track3: Track
    ):
        queue.add_track([track1, track2, track3])
        queue.remove_track(track2)
        assert len(queue.tracks) == 2
        assert queue.tracks[0] == track1
        assert queue.tracks[1] == track3

    def test_remove_track_non_existent(
        self, queue: Queue, track1: Track, track2: Track
    ):
        queue.add_track(track1)
        queue.remove_track(track2)
        assert len(queue.tracks) == 1
        assert queue.tracks[0] is track1

    def test_remove_track_empty_queue(self, queue: Queue, track1: Track):
        queue.remove_track(track1)
        assert len(queue.tracks) == 0

    def test_remove_track_only_match(self, queue: Queue, track1: Track):
        queue.add_track(track1)
        queue.remove_track(track1)
        assert len(queue.tracks) == 0
        assert queue.get_current_track() is None

    def test_remove_track_duplicates_removes_all(
        self, queue: Queue, track1: Track, track2: Track
    ):
        queue.add_track([track1, track1, track2])
        queue.remove_track(track1)
        assert len(queue.tracks) == 1
        assert queue.tracks[0] == track2

    def test_remove_track_does_not_affect_background(
        self, queue: Queue, track1: Track, track2: Track
    ):
        queue.add_background_track(track1)
        queue.add_background_track(track2)
        queue.add_track([track1, track2])
        queue.remove_track(track1)
        assert len(queue.tracks) == 1
        assert len(queue.background_tracks) == 2
