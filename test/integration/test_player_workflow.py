from test.unit.conftest import FakePlayer
from harpi.application.player_service import PlayerService


async def test_full_play_skip_stop_workflow():
    resolver = RealResolver()
    player = FakePlayer()
    svc = PlayerService(resolver=resolver, player=player)

    await svc.play("link1")
    await svc.play("link2")
    svc.skip()
    svc.stop()

    assert svc.queue.get_current_track() is None
    assert player.is_stopped is True
