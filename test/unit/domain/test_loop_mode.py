import pytest

from harpi.domain.loop_mode import LoopMode


class TestLoopMode:
    def test_loop_mode_values_are_strings(self):
        for mode in LoopMode:
            assert isinstance(mode.value, str)

    def test_loop_mode_equality(self):
        assert LoopMode.TRACK == LoopMode.TRACK
        assert LoopMode.QUEUE == LoopMode.QUEUE
        assert LoopMode.OFF == LoopMode.OFF

    def test_loop_mode_inequality(self):
        assert LoopMode.TRACK != LoopMode.QUEUE
        assert LoopMode.QUEUE != LoopMode.OFF
        assert LoopMode.OFF != LoopMode.TRACK

    def test_loop_mode_from_string(self):
        assert LoopMode("track") == LoopMode.TRACK
        assert LoopMode("queue") == LoopMode.QUEUE
        assert LoopMode("off") == LoopMode.OFF

    def test_loop_mode_invalid_string_raises(self):
        with pytest.raises(ValueError):
            LoopMode("invalid")
