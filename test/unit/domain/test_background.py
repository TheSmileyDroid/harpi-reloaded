import pytest

from harpi.domain.background_track_id import BackgroundTrackId
from harpi.domain.loop_mode import LoopMode
from harpi.domain.track_metadata import TrackMetadata, Source
from harpi.domain.background import BackgroundEntry, Background


class TestBackgroundEntry:
    def test_creates_entry_with_metadata_and_loop_mode(self):
        metadata = TrackMetadata(
            source=Source.YOUTUBE,
            link="https://youtu.be/abc",
            title="Test Track",
            duration=120,
        )
        entry = BackgroundEntry(
            id=BackgroundTrackId(),
            metadata=metadata,
            loop_mode=LoopMode.TRACK,
        )
        assert entry.metadata == metadata
        assert entry.loop_mode == LoopMode.TRACK
        assert isinstance(entry.id, BackgroundTrackId)

    def test_default_loop_mode_is_off(self):
        metadata = TrackMetadata(source=Source.YOUTUBE, link="https://youtu.be/abc")
        entry = BackgroundEntry(id=BackgroundTrackId(), metadata=metadata)
        assert entry.loop_mode == LoopMode.OFF

    def test_equality_by_id(self):
        bt_id = BackgroundTrackId()
        metadata = TrackMetadata(source=Source.YOUTUBE, link="https://youtu.be/abc")
        entry1 = BackgroundEntry(id=bt_id, metadata=metadata, loop_mode=LoopMode.TRACK)
        entry2 = BackgroundEntry(id=bt_id, metadata=metadata, loop_mode=LoopMode.QUEUE)
        assert entry1 == entry2

    def test_inequality_different_id(self):
        metadata = TrackMetadata(source=Source.YOUTUBE, link="https://youtu.be/abc")
        entry1 = BackgroundEntry(id=BackgroundTrackId(), metadata=metadata)
        entry2 = BackgroundEntry(id=BackgroundTrackId(), metadata=metadata)
        assert entry1 != entry2


class TestBackground:
    def test_starts_empty(self):
        bg = Background()
        assert bg.entries == []

    def test_add_entry(self):
        bg = Background()
        metadata = TrackMetadata(source=Source.YOUTUBE, link="https://youtu.be/abc")
        entry = BackgroundEntry(id=BackgroundTrackId(), metadata=metadata)
        bg.add_entry(entry)
        assert len(bg.entries) == 1
        assert bg.entries[0] == entry

    def test_remove_entry_by_id(self):
        bg = Background()
        bt_id = BackgroundTrackId()
        metadata = TrackMetadata(source=Source.YOUTUBE, link="https://youtu.be/abc")
        entry = BackgroundEntry(id=bt_id, metadata=metadata)
        bg.add_entry(entry)
        removed = bg.remove_entry(bt_id)
        assert removed == entry
        assert bg.entries == []

    def test_remove_entry_not_found_raises(self):
        bg = Background()
        with pytest.raises(KeyError):
            bg.remove_entry(BackgroundTrackId())

    def test_get_entry_by_id(self):
        bg = Background()
        bt_id = BackgroundTrackId()
        metadata = TrackMetadata(source=Source.YOUTUBE, link="https://youtu.be/abc")
        entry = BackgroundEntry(id=bt_id, metadata=metadata)
        bg.add_entry(entry)
        assert bg.get_entry(bt_id) == entry

    def test_get_entry_not_found_returns_none(self):
        bg = Background()
        assert bg.get_entry(BackgroundTrackId()) is None

    def test_clear_entries(self):
        bg = Background()
        metadata = TrackMetadata(source=Source.YOUTUBE, link="https://youtu.be/abc")
        bg.add_entry(BackgroundEntry(id=BackgroundTrackId(), metadata=metadata))
        bg.add_entry(BackgroundEntry(id=BackgroundTrackId(), metadata=metadata))
        bg.clear()
        assert bg.entries == []

    def test_entries_returns_copy(self):
        bg = Background()
        metadata = TrackMetadata(source=Source.YOUTUBE, link="https://youtu.be/abc")
        bg.add_entry(BackgroundEntry(id=BackgroundTrackId(), metadata=metadata))
        entries = bg.entries
        entries.clear()
        assert len(bg.entries) == 1
