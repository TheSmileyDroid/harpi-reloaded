from uuid import UUID
from dataclasses import FrozenInstanceError
import pytest

from harpi.domain.track import Track, Source, validate_volume


class TestTrackCreation:
    def test_track_added_with_required_fields(self):
        track = Track(
            source=Source.YOUTUBE,
            link="https://youtu.be/wPQEeBAXou0?si=rJZmNcFc5RwQyo4K",
        )
        assert track.link == "https://youtu.be/wPQEeBAXou0?si=rJZmNcFc5RwQyo4K"
        assert track.source == Source.YOUTUBE
        assert type(track.id) is UUID

    def test_track_resolved_title_and_duration(self):
        track = Track(
            link="https://youtu.be/abc",
            title="LOFI BEATS TO STUDY TO 1H",
            duration=3600,
            source=Source.YOUTUBE,
        )
        assert track.title == "LOFI BEATS TO STUDY TO 1H"
        assert track.duration == 3600

    def test_track_missing_link_raises(self):
        with pytest.raises(TypeError):
            Track(source=Source.YOUTUBE)  # ty:ignore[missing-argument]

    def test_track_missing_source_raises(self):
        with pytest.raises(TypeError):
            Track(link="https://youtu.be/abc")  # ty:ignore[missing-argument]


class TestTrackImmutability:
    def test_track_is_immutable(self):
        track = Track(source=Source.YOUTUBE, link="https://youtu.be/wPQEeBAXou0")
        with pytest.raises(FrozenInstanceError):
            track.link = "https://www.youtube.com/watch?v=5Duje_sZko8"  # ty:ignore[invalid-assignment]


class TestTrackEquality:
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

    def test_track_equality_different_type(self):
        track1 = Track(source=Source.YOUTUBE, link="https://youtu.be/wPQEeBAXou0")
        assert track1 != "Just a string"


class TestSourceId:
    @pytest.mark.parametrize(
        ("link", "source", "expected"),
        [
            # YOUTUBE — short form
            ("https://youtu.be/wPQEeBAXou0", Source.YOUTUBE, "wPQEeBAXou0"),
            (
                "https://youtu.be/wPQEeBAXou0?si=rJZmNcFc5RwQyo4K",
                Source.YOUTUBE,
                "wPQEeBAXou0",
            ),
            ("https://youtu.be/wPQEeBAXou0?list=PLabc", Source.YOUTUBE, "wPQEeBAXou0"),
            (
                "https://www.youtube.com/watch?v=wPQEeBAXou0",
                Source.YOUTUBE,
                "wPQEeBAXou0",
            ),
            (
                "https://youtube.com/watch?v=wPQEeBAXou0&list=PLabc",
                Source.YOUTUBE,
                "wPQEeBAXou0",
            ),
            (
                "https://youtube.com/watch?v=wPQEeBAXou0&t=30s",
                Source.YOUTUBE,
                "wPQEeBAXou0",
            ),
            (
                "https://youtube.com/watch?v=wPQEeBAXou0&si=abc&t=30s",
                Source.YOUTUBE,
                "wPQEeBAXou0",
            ),
            # YOUTUBE — /embed/ and /shorts/
            ("https://youtube.com/embed/wPQEeBAXou0", Source.YOUTUBE, "wPQEeBAXou0"),
            ("https://youtube.com/shorts/wPQEeBAXou0", Source.YOUTUBE, "wPQEeBAXou0"),
            # YOUTUBE — boundary/edge
            ("https://youtu.be/", Source.YOUTUBE, ""),
            ("youtu.be", Source.YOUTUBE, "youtu.be"),
            ("https://not-youtube.unknown", Source.YOUTUBE, ""),
            # SPOTIFY
            (
                "https://open.spotify.com/track/4WvbyZqjR4XWg45H",
                Source.SPOTIFY,
                "4WvbyZqjR4XWg45H",
            ),
            (
                "https://open.spotify.com/track/4WvbyZqjR4XWg45H?si=abc",
                Source.SPOTIFY,
                "4WvbyZqjR4XWg45H",
            ),
            # BVA: empty link
            ("", Source.YOUTUBE, ""),
            ("", Source.SPOTIFY, ""),
            # BVA: link with only query params (youtu.be doesn't parse v= param)
            ("https://youtu.be/?v=abc", Source.YOUTUBE, ""),
            # BVA: spotify with no track segment
            ("https://open.spotify.com/", Source.SPOTIFY, ""),
        ],
    )
    def test_source_id(self, link: str, source: Source, expected: str):
        track = Track(link=link, source=source)
        assert track.source_id == expected


class TestValidateVolumeBVA:
    @pytest.mark.parametrize(
        "value",
        [
            pytest.param(0.0, id="minimum"),
            pytest.param(0.001, id="just-above-minimum"),
            pytest.param(0.5, id="midpoint"),
            pytest.param(0.999, id="just-below-maximum"),
            pytest.param(1.0, id="maximum"),
        ],
    )
    def test_valid_volumes_accepted(self, value: float):
        validate_volume(value)

    @pytest.mark.parametrize(
        "value",
        [
            pytest.param(-0.1, id="below-minimum"),
            pytest.param(1.1, id="above-maximum"),
            pytest.param(-1.0, id="far-below-minimum"),
            pytest.param(2.0, id="far-above-maximum"),
        ],
    )
    def test_invalid_volumes_rejected(self, value: float):
        with pytest.raises(ValueError, match="must be between"):
            validate_volume(value)

    def test_custom_name_in_error(self):
        with pytest.raises(ValueError, match="Duck level"):
            validate_volume(-0.1, "Duck level")
