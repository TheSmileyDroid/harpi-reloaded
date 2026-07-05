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

        expected = (
            np.clip(
                np.frombuffer(frame, dtype=np.int16).astype(np.float32) * 2,
                -32768,
                32767,
            )
            .astype(np.int16)
            .tobytes()
        )
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
        mixer = MixedAudioSource(processes=[fg_proc, bg_proc], volumes=[1.0, 1.0])

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

        expected = (
            (np.frombuffer(frame, dtype=np.int16).astype(np.float32) * 0.001)
            .astype(np.int16)
            .tobytes()
        )
        assert result == expected

    def test_volume_just_below_maximum(self):
        frame = _frame(amplitude=0.5)
        source = FakeProcess(frame)
        mixer = MixedAudioSource(processes=[source], volumes=[0.999])

        result = mixer.read()

        expected = (
            (np.frombuffer(frame, dtype=np.int16).astype(np.float32) * 0.999)
            .astype(np.int16)
            .tobytes()
        )
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

        expected = (
            (np.frombuffer(frame, dtype=np.int16).astype(np.float32) * 0.5)
            .astype(np.int16)
            .tobytes()
        )
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

        expected = (
            np.clip(
                np.frombuffer(_silent_frame(), dtype=np.int16).astype(np.float32)
                + np.frombuffer(bg, dtype=np.int16).astype(np.float32) * 0.5,
                -32768,
                32767,
            )
            .astype(np.int16)
            .tobytes()
        )
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

    def test_source_count_tracks_add_and_remove(self):
        proc1 = FakeProcess(_silent_frame())
        proc2 = FakeProcess(_silent_frame())
        mixer = MixedAudioSource(processes=[proc1], volumes=[1.0])

        mixer.add_source(proc2, 0.5)
        assert mixer.source_count == 2

        mixer.remove_source(1)
        assert mixer.source_count == 1

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


class TestMixedAudioSourceSourceLifecycle:
    def test_on_source_finished_fires_once_per_exhausted_source(self):
        fg_proc = FakeProcess(_frame())
        bg_proc = FakeProcess(_frame() * 3)
        finished: list[tuple] = []
        mixer = MixedAudioSource(
            processes=[fg_proc, bg_proc],
            volumes=[1.0, 1.0],
            on_source_finished=lambda proc, active: finished.append((proc, active)),
        )

        mixer.read()
        mixer.read()
        mixer.read()

        assert finished == [(fg_proc, 1)]

    def test_on_source_finished_reports_zero_active_for_last_source(self):
        proc = FakeProcess(_frame())
        finished: list[tuple] = []
        mixer = MixedAudioSource(
            processes=[proc],
            volumes=[1.0],
            on_source_finished=lambda p, active: finished.append((p, active)),
        )

        mixer.read()
        mixer.read()

        assert finished == [(proc, 0)]

    def test_replace_source_swaps_process_and_returns_old(self):
        old_proc = FakeProcess(_frame())
        bg_proc = FakeProcess(_silent_frame() * 4)
        mixer = MixedAudioSource(processes=[old_proc, bg_proc], volumes=[1.0, 1.0])
        mixer.read()
        mixer.read()

        frame = _frame(amplitude=0.4)
        new_proc = FakeProcess(frame * 2)
        returned = mixer.replace_source(0, new_proc, 1.0)
        result = mixer.read()

        assert returned is old_proc
        assert result == frame

    def test_replace_source_applies_new_volume(self):
        old_proc = FakeProcess(_frame())
        mixer = MixedAudioSource(processes=[old_proc], volumes=[1.0])
        mixer.read()
        mixer.read()

        frame = _frame(amplitude=0.5)
        new_proc = FakeProcess(frame)
        mixer.replace_source(0, new_proc, 0.5)
        result = mixer.read()

        expected = (
            (np.frombuffer(frame, dtype=np.int16).astype(np.float32) * 0.5)
            .astype(np.int16)
            .tobytes()
        )
        assert result == expected

    def test_replace_source_rejects_invalid_volume(self):
        proc = FakeProcess(_frame())
        mixer = MixedAudioSource(processes=[proc], volumes=[1.0])

        with pytest.raises(ValueError):
            mixer.replace_source(0, FakeProcess(_frame()), 1.5)


class TestMixedAudioSourceEdgeCases:
    def test_read_when_stdout_is_none(self):
        class _NoStdoutProcess:
            stdout = None

            def kill(self):
                pass

            def wait(self, timeout: float = 1):
                pass

        mixer = MixedAudioSource(processes=[_NoStdoutProcess()], volumes=[1.0])

        result = mixer.read()

        assert result == b""

    def test_cleanup_exception_handling(self):
        class FailingProcess:
            stdout = None

            def kill(self):
                raise OSError("kill failed")

            def wait(self, timeout=1):
                raise OSError("wait failed")

        proc = FailingProcess()
        mixer = MixedAudioSource(processes=[proc], volumes=[1.0])

        mixer.cleanup()

        assert mixer.source_count == 0
