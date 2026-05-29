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


class TestQueue:
    def test_adds_track_to_queue(self, queue: Queue, track1: Track, track2: Track):
        queue.add_track(track1)
        assert len(queue.tracks) == 1
        assert queue.tracks[0] == track1

        queue.add_track(track2)
        assert len(queue.tracks) == 2
        assert queue.tracks[1] == track2

    def test_get_current_track(self, queue: Queue, track1: Track, track2: Track):
        queue.add_track(track1)
        queue.add_track(track2)
        assert queue.get_current_track() == track1

    def test_adds_multiple_tracks_to_queue(
        self, queue: Queue, track1: Track, track2: Track, track3: Track
    ):
        queue.add_track([track1, track2, track3])
        assert len(queue.tracks) == 3
        assert queue.tracks[0] == track1
        assert queue.tracks[1] == track2
        assert queue.tracks[2] == track3

    def test_clears_tracks_from_queue(self, queue: Queue, track1: Track, track2: Track):
        queue.add_track([track1, track2])
        queue.clear_tracks()
        assert len(queue.tracks) == 0

    def test_sets_background_tracks_on_queue(
        self, queue: Queue, track1: Track, track2: Track
    ):
        queue.set_background_tracks([track1, track2])
        assert len(queue.background_tracks) == 2
        assert queue.background_tracks[0] == track1
        assert queue.background_tracks[1] == track2

    def test_clears_background_tracks_on_queue(
        self, queue: Queue, track1: Track, track2: Track
    ):
        queue.set_background_tracks([track1, track2])
        queue.clear_background_tracks()
        assert len(queue.background_tracks) == 0

    def test_default_background_tracks_is_empty(self, queue: Queue):
        assert len(queue.background_tracks) == 0

    def test_default_loop_mode_is_off(self, queue: Queue):
        assert queue.loop_mode == LoopMode.OFF

    def test_get_current_track_empty_queue(self, queue: Queue):
        assert queue.get_current_track() is None

    def test_skip_track(self, queue: Queue, track1: Track, track2: Track):
        queue.add_track([track1, track2])
        assert queue.get_current_track() == track1
        assert queue.skip_track() is track1
        assert queue.get_current_track() == track2
        assert queue.skip_track() is track2
        assert queue.get_current_track() is None

    def test_skip_track_empty_queue(self, queue: Queue):
        assert queue.skip_track() is None

    def test_loop_track_skips(self, queue: Queue, track1: Track):
        queue.set_loop_mode(LoopMode.TRACK)
        queue.add_track(track1)
        assert queue.skip_track() is track1
        assert queue.get_current_track() is track1

    def test_loop_queue_skips(self, queue: Queue, track1: Track, track2: Track):
        queue.set_loop_mode(LoopMode.QUEUE)
        queue.add_track([track1, track2])
        assert queue.skip_track() is track1
        assert queue.get_current_track() is track2
        assert queue.skip_track() is track2
        assert queue.get_current_track() is track1

    def test_loop_off_skips(self, queue: Queue, track1: Track, track2: Track):
        queue.set_loop_mode(LoopMode.OFF)
        queue.add_track([track1, track2])
        assert queue.skip_track() is track1
        assert queue.get_current_track() is track2
        assert queue.skip_track() is track2
        assert queue.get_current_track() is None

    def test_skip_track_single_off(self, queue: Queue, track1: Track):
        queue.add_track(track1)
        assert queue.skip_track() is track1
        assert queue.get_current_track() is None

    def test_skip_track_queue_exhausted(self, queue: Queue, track1: Track):
        queue.add_track(track1)
        queue.skip_track()
        assert queue.skip_track() is None

    def test_loop_queue_skips_single(self, queue: Queue, track1: Track):
        queue.set_loop_mode(LoopMode.QUEUE)
        queue.add_track(track1)
        assert queue.skip_track() is track1
        assert queue.get_current_track() is track1

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

    def test_add_track_empty_list(self, queue: Queue):
        queue.add_track([])
        assert len(queue.tracks) == 0

    def test_remove_track(
        self, queue: Queue, track1: Track, track2: Track, track3: Track
    ):
        queue.add_track([track1, track2, track3])
        queue.remove_track(track2)
        assert len(queue.tracks) == 2
        assert queue.tracks[0] == track1
        assert queue.tracks[1] == track3

    def test_queue_preserves_order_after_multiple_adds(self):
        queue = Queue()
        tracks = [
            Track(link=f"l{i}", title=f"t{i}", duration=60, source=Source.YOUTUBE)
            for i in range(5)
        ]
        queue.add_track(tracks)
        assert queue.tracks == tracks  # state check
        assert queue.get_current_track() == tracks[0]

    def test_queue_isolation_between_instances(self):
        q1, q2 = Queue(), Queue()
        t1 = Track(link="a", title="A", duration=60, source=Source.YOUTUBE)
        q1.add_track([t1])
        assert q2.get_current_track() is None
