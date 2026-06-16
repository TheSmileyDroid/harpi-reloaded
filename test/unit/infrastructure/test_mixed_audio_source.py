import io
import numpy as np
import pytest
from harpi.infrastructure.mixed_audio_source import MixedAudioSource, PCM_FRAME_SIZE


class FakeProcess:
    def __init__(self, data: bytes):
        self.stdout = io.BytesIO(data)
        self._killed = False

    def kill(self):
        self._killed = True

    def wait(self, timeout: float = 1):
        pass


def _frame(amplitude: float = 0.5, freq: float = 440) -> bytes:
    stereo_pairs = PCM_FRAME_SIZE // 4
    t = np.linspace(0, 1 / 100, stereo_pairs, False)
    mono = (amplitude * 32767 * np.sin(2 * np.pi * freq * t)).astype(np.int16)
    stereo = np.column_stack([mono, mono]).ravel()
    return stereo.tobytes()


def _silent_frame() -> bytes:
    return b"\x00" * PCM_FRAME_SIZE


class TestMixedAudioSourceRead:
    def test_read_returns_pcm_with_one_source(self):
        frame = _frame(amplitude=0.5)
        source = FakeProcess(frame)
        mixer = MixedAudioSource(processes=[source], volumes=[1.0])

        result = mixer.read()

        assert len(result) == PCM_FRAME_SIZE
        assert result == frame

    def test_read_mixes_two_sources(self):
        frame = _frame(amplitude=0.3)
        source1 = FakeProcess(frame)
        source2 = FakeProcess(frame)
        mixer = MixedAudioSource(processes=[source1, source2], volumes=[1.0, 1.0])

        result = mixer.read()

        expected = np.clip(
            np.frombuffer(frame, dtype=np.int16).astype(np.float32) * 2,
            -32768,
            32767,
        ).astype(np.int16).tobytes()
        assert result == expected

    def test_read_returns_empty_when_no_sources(self):
        mixer = MixedAudioSource(processes=[], volumes=[])

        result = mixer.read()

        assert result == b""

    def test_read_continues_when_one_source_exhausted(self):
        fg_frame = _silent_frame()
        bg_frame = _frame(amplitude=0.3)
        fg_proc = FakeProcess(fg_frame)
        bg_proc = FakeProcess(bg_frame * 2)
        mixer = MixedAudioSource(
            processes=[fg_proc, bg_proc], volumes=[1.0, 1.0]
        )

        mixer.read()
        result = mixer.read()

        assert len(result) == PCM_FRAME_SIZE
        assert result == bg_frame


class TestMixedAudioSourceVolumeBVA:
    def test_volume_minimum(self):
        frame = _frame(amplitude=0.5)
        source = FakeProcess(frame)
        mixer = MixedAudioSource(processes=[source], volumes=[0.0])

        result = mixer.read()

        assert result == _silent_frame()

    def test_volume_just_above_minimum(self):
        frame = _frame(amplitude=0.5)
        source = FakeProcess(frame)
        mixer = MixedAudioSource(processes=[source], volumes=[0.001])

        result = mixer.read()

        expected = (np.frombuffer(frame, dtype=np.int16).astype(np.float32) * 0.001).astype(np.int16).tobytes()
        assert result == expected

    def test_volume_just_below_maximum(self):
        frame = _frame(amplitude=0.5)
        source = FakeProcess(frame)
        mixer = MixedAudioSource(processes=[source], volumes=[0.999])

        result = mixer.read()

        expected = (np.frombuffer(frame, dtype=np.int16).astype(np.float32) * 0.999).astype(np.int16).tobytes()
        assert result == expected

    def test_volume_maximum(self):
        frame = _frame(amplitude=0.5)
        source = FakeProcess(frame)
        mixer = MixedAudioSource(processes=[source], volumes=[1.0])

        result = mixer.read()

        assert result == frame

    def test_volume_below_minimum_raises(self):
        source = FakeProcess(_silent_frame())
        with pytest.raises(ValueError):
            MixedAudioSource(processes=[source], volumes=[-0.1])

    def test_volume_above_maximum_raises(self):
        source = FakeProcess(_silent_frame())
        with pytest.raises(ValueError):
            MixedAudioSource(processes=[source], volumes=[1.1])


class TestMixedAudioSourceDynamic:
    def test_volume_change_reflects_immediately(self):
        frame = _frame(amplitude=0.5)
        source = FakeProcess(frame * 2)
        mixer = MixedAudioSource(processes=[source], volumes=[1.0])
        mixer.read()

        mixer.set_volume(0, 0.5)
        result = mixer.read()

        expected = (np.frombuffer(frame, dtype=np.int16).astype(np.float32) * 0.5).astype(np.int16).tobytes()
        assert result == expected

    def test_add_source_mid_playback(self):
        fg = _silent_frame()
        bg = _frame(amplitude=0.3)
        fg_proc = FakeProcess(fg * 2)
        mixer = MixedAudioSource(processes=[fg_proc], volumes=[1.0])
        mixer.read()

        bg_proc = FakeProcess(bg)
        mixer.add_source(bg_proc, 0.5)
        result = mixer.read()

        expected = np.clip(
            np.frombuffer(_silent_frame(), dtype=np.int16).astype(np.float32)
            + np.frombuffer(bg, dtype=np.int16).astype(np.float32) * 0.5,
            -32768, 32767,
        ).astype(np.int16).tobytes()
        assert result == expected

    def test_remove_source_mid_playback(self):
        fg = _frame(amplitude=0.3)
        bg = _frame(amplitude=0.3)
        fg_proc = FakeProcess(fg * 2)
        bg_proc = FakeProcess(bg * 2)
        mixer = MixedAudioSource(processes=[fg_proc, bg_proc], volumes=[1.0, 1.0])
        mixer.read()

        removed = mixer.remove_source(1)
        result = mixer.read()

        assert removed is bg_proc
        assert result == fg

    def test_cleanup_terminates_processes(self):
        frame = _silent_frame()
        proc1 = FakeProcess(frame)
        proc2 = FakeProcess(frame)
        mixer = MixedAudioSource(processes=[proc1, proc2], volumes=[1.0, 1.0])

        mixer.cleanup()

        assert proc1._killed
        assert proc2._killed

    def test_cleanup_idempotent(self):
        proc = FakeProcess(_silent_frame())
        mixer = MixedAudioSource(processes=[proc], volumes=[1.0])

        mixer.cleanup()
        mixer.cleanup()

        assert proc._killed
