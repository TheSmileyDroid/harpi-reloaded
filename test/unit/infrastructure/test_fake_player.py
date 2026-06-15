import pytest
from test.unit.conftest import FakePlayer


class TestFakePlayerVolumeBVA:
    def test_volume_minimum(self):
        player = FakePlayer()
        player.set_volume(0.0)
        assert player.volume == 0.0

    def test_volume_just_above_minimum(self):
        player = FakePlayer()
        player.set_volume(0.001)
        assert player.volume == 0.001

    def test_volume_just_below_maximum(self):
        player = FakePlayer()
        player.set_volume(0.999)
        assert player.volume == 0.999

    def test_volume_maximum(self):
        player = FakePlayer()
        player.set_volume(1.0)
        assert player.volume == 1.0

    def test_volume_below_minimum_raises(self):
        player = FakePlayer()
        with pytest.raises(ValueError):
            player.set_volume(-0.1)

    def test_volume_above_maximum_raises(self):
        player = FakePlayer()
        with pytest.raises(ValueError):
            player.set_volume(1.1)


class TestFakePlayerBackgroundVolumeBVA:
    def test_background_volume_minimum(self):
        player = FakePlayer()
        player.set_background_volume(0.0)
        assert player.background_volume == 0.0

    def test_background_volume_just_above_minimum(self):
        player = FakePlayer()
        player.set_background_volume(0.001)
        assert player.background_volume == 0.001

    def test_background_volume_just_below_maximum(self):
        player = FakePlayer()
        player.set_background_volume(0.999)
        assert player.background_volume == 0.999

    def test_background_volume_maximum(self):
        player = FakePlayer()
        player.set_background_volume(1.0)
        assert player.background_volume == 1.0

    def test_background_volume_below_minimum_raises(self):
        player = FakePlayer()
        with pytest.raises(ValueError):
            player.set_background_volume(-0.1)

    def test_background_volume_above_maximum_raises(self):
        player = FakePlayer()
        with pytest.raises(ValueError):
            player.set_background_volume(1.1)


class TestFakePlayerDuckLevelBVA:
    def test_duck_level_minimum(self):
        player = FakePlayer()
        player.set_ducking(0.0)
        assert player._duck_level == 0.0

    def test_duck_level_just_above_minimum(self):
        player = FakePlayer()
        player.set_ducking(0.001)
        assert player._duck_level == 0.001

    def test_duck_level_just_below_maximum(self):
        player = FakePlayer()
        player.set_ducking(0.999)
        assert player._duck_level == 0.999

    def test_duck_level_maximum(self):
        player = FakePlayer()
        player.set_ducking(1.0)
        assert player._duck_level == 1.0

    def test_duck_level_below_minimum_raises(self):
        player = FakePlayer()
        with pytest.raises(ValueError):
            player.set_ducking(-0.1)

    def test_duck_level_above_maximum_raises(self):
        player = FakePlayer()
        with pytest.raises(ValueError):
            player.set_ducking(1.1)


class TestFakePlayerDuckCycle:
    async def test_duck_saves_and_reduces_background_volume(self):
        player = FakePlayer()
        player.background_volume = 0.8
        await player.duck()
        assert player.is_ducking is True
        assert player.background_volume == player._duck_level

    async def test_unduck_restores_saved_background_volume(self):
        player = FakePlayer()
        player.background_volume = 0.8
        await player.duck()
        await player.unduck()
        assert player.is_ducking is False
        assert player.background_volume == 0.8

    async def test_duck_unduck_duck_cycle_restores_on_each_unduck(self):
        player = FakePlayer()
        player.background_volume = 0.8
        await player.duck()
        await player.unduck()
        assert player.background_volume == 0.8
        player.background_volume = 0.5
        await player.duck()
        assert player.is_ducking is True
        assert player.background_volume == player._duck_level
        await player.unduck()
        assert player.is_ducking is False
        assert player.background_volume == 0.5

    async def test_double_duck_is_idempotent(self):
        player = FakePlayer()
        player.background_volume = 0.8
        await player.duck()
        saved = player._saved_background_volume
        await player.duck()
        assert player.is_ducking is True
        assert player._saved_background_volume == saved

    async def test_double_unduck_does_not_crash(self):
        player = FakePlayer()
        await player.duck()
        await player.unduck()
        await player.unduck()
        assert player.is_ducking is False
