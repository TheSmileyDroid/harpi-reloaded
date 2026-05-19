from uuid import UUID
from pydantic import ValidationError
import pytest

from harpi.domain.track import Track, Source


class TestTrack:
    def test_track_added_with_required_fields(self):
        track = Track(
            source=Source.YOUTUBE,
            link="https://youtu.be/wPQEeBAXou0?si=rJZmNcFc5RwQyo4K",
        )
        assert track.link == "https://youtu.be/wPQEeBAXou0?si=rJZmNcFc5RwQyo4K"
        assert track.source == Source.YOUTUBE
        assert type(track.id) is UUID

    def test_track_equality(self):
        track1 = Track(source=Source.YOUTUBE, link="https://youtu.be/wPQEeBAXou0")
        track2 = Track(
            source=Source.YOUTUBE,
            link="https://youtu.be/wPQEeBAXou0?si=rJZmNcFc5RwQyo4K",
        )
        track3 = Track(
            source=Source.YOUTUBE, link="https://www.youtube.com/watch?v=wPQEeBAXou0"
        )
        assert track1 == track2 and track2 == track3

    def test_track_equality_different_sources(self):
        track1 = Track(source=Source.YOUTUBE, link="https://youtu.be/wPQEeBAXou0")
        track2 = Track(
            source=Source.SPOTIFY, link="https://open.spotify.com/track/wPQEeBAXou0"
        )
        assert track1 != track2

    def test_track_equality_different_source_ids(self):
        track1 = Track(source=Source.YOUTUBE, link="https://youtu.be/wPQEeBAXou0")

        track2 = Track(source=Source.YOUTUBE, link="https://youtu.be/25Duje_sZko8")

        assert track1 != track2

    def test_track_is_immutable(self):
        track = Track(source=Source.YOUTUBE, link="https://youtu.be/wPQEeBAXou0")
        with pytest.raises((ValidationError)):
            track.link = "https://www.youtube.com/watch?v=5Duje_sZko8"
