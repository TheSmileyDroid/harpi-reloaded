from uuid import UUID
import pytest

from harpi.domain.track_metadata import TrackMetadata, Source


class TestTrackMetadataCreation:
    def test_track_metadata_created_with_required_fields(self):
        metadata = TrackMetadata(
            source=Source.YOUTUBE,
            link="https://youtu.be/wPQEeBAXou0?si=rJZmNcFc5RwQyo4K",
        )
        assert metadata.link == "https://youtu.be/wPQEeBAXou0?si=rJZmNcFc5RwQyo4K"
        assert metadata.source == Source.YOUTUBE
        assert type(metadata.id) is UUID

    def test_track_metadata_with_optional_fields(self):
        metadata = TrackMetadata(
            link="https://youtu.be/abc",
            title="LOFI BEATS TO STUDY TO 1H",
            duration=3600,
            source=Source.YOUTUBE,
        )
        assert metadata.title == "LOFI BEATS TO STUDY TO 1H"
        assert metadata.duration == 3600


class TestTrackMetadataEquality:
    def test_instances_with_same_id_are_equal(self):
        meta1 = TrackMetadata(
            source=Source.YOUTUBE, link="https://youtu.be/wPQEeBAXou0"
        )
        meta2 = meta1
        assert meta1 == meta2

    def test_instances_with_same_source_id_are_not_equal(self):
        meta1 = TrackMetadata(
            source=Source.YOUTUBE, link="https://youtu.be/wPQEeBAXou0"
        )
        meta2 = TrackMetadata(
            source=Source.YOUTUBE,
            link="https://youtu.be/wPQEeBAXou0?si=rJZmNcFc5RwQyo4K",
        )
        meta3 = TrackMetadata(
            source=Source.YOUTUBE, link="https://www.youtube.com/watch?v=wPQEeBAXou0"
        )
        assert meta1 != meta2 != meta3

    def test_equality_different_sources(self):
        meta1 = TrackMetadata(
            source=Source.YOUTUBE, link="https://youtu.be/wPQEeBAXou0"
        )
        meta2 = TrackMetadata(
            source=Source.SPOTIFY, link="https://open.spotify.com/track/wPQEeBAXou0"
        )
        assert meta1 != meta2

    def test_equality_different_source_ids(self):
        meta1 = TrackMetadata(
            source=Source.YOUTUBE, link="https://youtu.be/wPQEeBAXou0"
        )
        meta2 = TrackMetadata(
            source=Source.YOUTUBE, link="https://youtu.be/25Duje_sZko8"
        )
        assert meta1 != meta2

    def test_equality_different_type(self):
        meta1 = TrackMetadata(
            source=Source.YOUTUBE, link="https://youtu.be/wPQEeBAXou0"
        )
        assert meta1 != "Just a string"


class TestSourceIdExtraction:
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
            # YOUTUBE — watch form
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
            # YOUTUBE — embed and shorts
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
            # BVA: link with only query params
            ("https://youtu.be/?v=abc", Source.YOUTUBE, ""),
            # BVA: spotify with no track segment
            ("https://open.spotify.com/", Source.SPOTIFY, ""),
        ],
    )
    def test_source_id(self, link: str, source: Source, expected: str):
        metadata = TrackMetadata(link=link, source=source)
        assert metadata.source_id == expected


class TestTrackMetadataHash:
    def test_hash_is_consistent(self):
        meta1 = TrackMetadata(
            link="https://youtu.be/abc", source=Source.YOUTUBE, title="A", duration=60
        )
        meta2 = TrackMetadata(
            link="https://youtu.be/abc", source=Source.YOUTUBE, title="A", duration=60
        )
        assert hash(meta1) == hash(meta2)

    def test_hash_usable_in_set(self):
        meta = TrackMetadata(
            link="https://youtu.be/abc", source=Source.YOUTUBE, title="A", duration=60
        )
        s = {meta}
        assert meta in s
