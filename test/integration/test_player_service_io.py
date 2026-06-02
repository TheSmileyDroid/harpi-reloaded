import pytest
from harpi.application.player_service import PlayerService
from harpi.domain.queue import LoopMode


@pytest.mark.integration
class TestPlayerServiceWithRealResolver:
    """Testa o PlayerService com resolver HTTP real."""

    @pytest.mark.asyncio
    async def test_play_with_real_resolver(self):
        from harpi.infrastructure.youtube_resolver import YoutubeResolver
        from test.unit.conftest import FakePlayer

        svc = PlayerService(resolver=YoutubeResolver(), player=FakePlayer())
        await svc.play("https://youtu.be/jNQXAC9IVRw")

        assert len(svc.queue.tracks) == 1
        track = svc.queue.get_current_track()
        assert track is not None
        assert track.title == "Me at the zoo"
        assert track.duration is not None
        assert track.resolved is True

    @pytest.mark.asyncio
    async def test_play_two_tracks_skips_correctly(self):
        from harpi.infrastructure.youtube_resolver import YoutubeResolver
        from test.unit.conftest import FakePlayer

        svc = PlayerService(resolver=YoutubeResolver(), player=FakePlayer())
        await svc.play("https://youtu.be/M8J9zHyyUYc")
        await svc.play("https://youtu.be/dQw4w9WgXcQ")

        assert len(svc.queue.tracks) == 2
        first = svc.queue.get_current_track()
        assert first is not None
        assert first.source_id == "M8J9zHyyUYc"

        await svc.skip()
        assert len(svc.queue.tracks) == 1
        current = svc.queue.get_current_track()
        assert current is not None
        assert current.source_id == "dQw4w9WgXcQ"

    @pytest.mark.asyncio
    async def test_stop_clears_after_real_play(self):
        from harpi.infrastructure.youtube_resolver import YoutubeResolver
        from test.unit.conftest import FakePlayer

        svc = PlayerService(resolver=YoutubeResolver(), player=FakePlayer())
        await svc.play("https://youtu.be/M8J9zHyyUYc")
        assert len(svc.queue.tracks) == 1

        await svc.stop()
        assert len(svc.queue.tracks) == 0

    @pytest.mark.asyncio
    async def test_loop_queue_with_real_tracks(self):
        from harpi.infrastructure.youtube_resolver import YoutubeResolver
        from test.unit.conftest import FakePlayer

        svc = PlayerService(resolver=YoutubeResolver(), player=FakePlayer())
        svc.queue.set_loop_mode(LoopMode.QUEUE)
        await svc.play("https://youtu.be/M8J9zHyyUYc")
        await svc.play("https://youtu.be/dQw4w9WgXcQ")

        await svc.skip()
        await svc.skip()
        await svc.skip()
        assert len(svc.queue.tracks) == 2
        current = svc.queue.get_current_track()
        assert current is not None
        assert current.source_id == "dQw4w9WgXcQ"
