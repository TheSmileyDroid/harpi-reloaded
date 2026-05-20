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

    def test_remove_track(
        self, queue: Queue, track1: Track, track2: Track, track3: Track
    ):
        queue.add_track([track1, track2, track3])
        queue.remove_track(track2)
        assert len(queue.tracks) == 2
        assert queue.tracks[0] == track1
        assert queue.tracks[1] == track3
