from harpi.domain.mixer import LoopMode
import pytest
from harpi.domain.mixer import Mixer
from harpi.domain.track import Track, Source


class TestMixer:
    @pytest.fixture()
    def mixer(self):
        return Mixer()

    @pytest.fixture()
    def track1(self):
        return Track(source=Source.YOUTUBE, link="https://youtu.be/wPQEeBAXou0")

    @pytest.fixture()
    def track2(self):
        return Track(source=Source.YOUTUBE, link="https://youtu.be/7wtfhZwyrcc")

    def test_adds_track_to_queue(self, mixer: Mixer, track1: Track, track2: Track):
        mixer.add_track(track1)
        assert len(mixer.tracks) == 1
        assert mixer.tracks[0] == track1

        mixer.add_track(track2)
        assert len(mixer.tracks) == 2
        assert mixer.tracks[1] == track2

    def test_get_current_track(self, mixer: Mixer, track1: Track, track2: Track):
        mixer.add_track(track1)
        mixer.add_track(track2)
        assert mixer.get_current_track() == track1

    def test_adds_multiple_tracks_to_queue(
        self, mixer: Mixer, track1: Track, track2: Track
    ):
        mixer.add_track([track1, track2])
        assert len(mixer.tracks) == 2
        assert mixer.tracks[0] == track1
        assert mixer.tracks[1] == track2

    def test_clears_tracks_from_queue(self, mixer: Mixer, track1: Track, track2: Track):
        mixer.add_track([track1, track2])
        mixer.clear_tracks()
        assert len(mixer.tracks) == 0

    def test_sets_background_tracks_on_mixer(
        self, mixer: Mixer, track1: Track, track2: Track
    ):
        mixer.set_background_tracks([track1, track2])
        assert len(mixer.background_tracks) == 2
        assert mixer.background_tracks[0] == track1
        assert mixer.background_tracks[1] == track2

    def test_clears_background_tracks_on_mixer(
        self, mixer: Mixer, track1: Track, track2: Track
    ):
        mixer.set_background_tracks([track1, track2])
        mixer.clear_background_tracks()
        assert len(mixer.background_tracks) == 0

    def test_get_current_track_empty_queue(self, mixer: Mixer):
        assert mixer.get_current_track() is None

    def test_skip_track(self, mixer: Mixer, track1: Track, track2: Track):
        mixer.add_track([track1, track2])
        assert mixer.get_current_track() == track1
        assert mixer.skip_track() is track1
        assert mixer.get_current_track() == track2
        assert mixer.skip_track() is track2
        assert mixer.get_current_track() is None

    def test_skip_track_empty_queue(self, mixer: Mixer):
        assert mixer.skip_track() is None

    def test_loop_track_skips(self, mixer: Mixer, track1: Track):
        mixer.set_loop_mode(LoopMode.TRACK)
        mixer.add_track(track1)
        assert mixer.skip_track() is track1
        assert mixer.get_current_track() is track1
