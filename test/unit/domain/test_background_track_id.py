from uuid import UUID

from harpi.domain.background_track_id import BackgroundTrackId


class TestBackgroundTrackId:
    def test_default_creates_unique_uuid(self):
        id1 = BackgroundTrackId()
        id2 = BackgroundTrackId()
        assert isinstance(id1.value, UUID)
        assert id1 != id2

    def test_explicit_uuid(self):
        uuid_val = UUID("12345678-1234-5678-1234-567812345678")
        bt_id = BackgroundTrackId(value=uuid_val)
        assert bt_id.value == uuid_val

    def test_equality_same_uuid(self):
        uuid_val = UUID("12345678-1234-5678-1234-567812345678")
        id1 = BackgroundTrackId(value=uuid_val)
        id2 = BackgroundTrackId(value=uuid_val)
        assert id1 == id2

    def test_inequality_different_uuid(self):
        id1 = BackgroundTrackId()
        id2 = BackgroundTrackId()
        assert id1 != id2

    def test_hash_consistent_with_equality(self):
        uuid_val = UUID("12345678-1234-5678-1234-567812345678")
        id1 = BackgroundTrackId(value=uuid_val)
        id2 = BackgroundTrackId(value=uuid_val)
        assert hash(id1) == hash(id2)

    def test_str_representation(self):
        uuid_val = UUID("12345678-1234-5678-1234-567812345678")
        bt_id = BackgroundTrackId(value=uuid_val)
        assert str(bt_id) == "12345678-1234-5678-1234-567812345678"

    def test_equality_with_non_background_track_id(self):
        bt_id = BackgroundTrackId()
        assert bt_id != "not a BackgroundTrackId"
        assert bt_id != 123
