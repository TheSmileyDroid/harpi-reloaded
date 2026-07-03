from harpi.domain.guild import Guild
from harpi.domain.queue import Queue
from harpi.domain.background import Background
from harpi.domain.track_metadata import TrackMetadata, Source


class TestGuild:
    def test_guild_holds_queue_and_background(self):
        guild = Guild(guild_id=12345)
        assert isinstance(guild.queue, Queue)
        assert isinstance(guild.background, Background)
        assert guild.guild_id == 12345

    def test_guild_queue_and_background_are_mutable(self):
        guild = Guild(guild_id=12345)
        metadata = TrackMetadata(
            source=Source.YOUTUBE,
            link="https://youtu.be/abc",
            title="Test",
            duration=120,
        )
        guild.queue.add_track(metadata)
        assert guild.queue.get_current_track() == metadata
