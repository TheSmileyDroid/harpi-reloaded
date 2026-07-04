from collections.abc import Callable
from typing import Any

import numpy as np
import discord
from discord.opus import Encoder

from harpi.domain.volume import validate_volume

PCM_FRAME_SIZE: int = Encoder.FRAME_SIZE


class MixedAudioSource(discord.AudioSource):
    def __init__(
        self,
        processes: list[Any],
        volumes: list[float],
        on_source_finished: Callable[[Any, int], None] | None = None,
    ):
        self._processes = list(processes)
        self._volumes = list(volumes)
        self._finished = [False] * len(self._processes)
        self._on_source_finished = on_source_finished
        for v in volumes:
            validate_volume(v, "Volume")

    def read(self) -> bytes:
        arrays = []
        finished_now: list[Any] = []
        for i, proc in enumerate(self._processes):
            if self._finished[i]:
                continue
            stdout = proc.stdout
            if stdout is None:
                self._finished[i] = True
                finished_now.append(proc)
                continue
            data = stdout.read(PCM_FRAME_SIZE)
            if not data or len(data) < PCM_FRAME_SIZE:
                self._finished[i] = True
                finished_now.append(proc)
                continue
            arrays.append(
                np.frombuffer(data, dtype=np.int16).astype(np.float32)
                * self._volumes[i]
            )
        if finished_now and self._on_source_finished is not None:
            active = sum(1 for done in self._finished if not done)
            for proc in finished_now:
                self._on_source_finished(proc, active)
        if not arrays:
            return b""
        mixed = np.clip(np.sum(arrays, axis=0), -32768, 32767).astype(np.int16)
        return mixed.tobytes()

    @property
    def source_count(self) -> int:
        return len(self._processes)

    def add_source(self, process: Any, volume: float) -> None:
        validate_volume(volume, "Volume")
        self._processes.append(process)
        self._volumes.append(volume)
        self._finished.append(False)

    def remove_source(self, index: int) -> Any:
        proc = self._processes.pop(index)
        self._volumes.pop(index)
        self._finished.pop(index)
        return proc

    def replace_source(self, index: int, process: Any, volume: float) -> Any:
        validate_volume(volume, "Volume")
        old = self._processes[index]
        self._processes[index] = process
        self._volumes[index] = volume
        self._finished[index] = False
        return old

    def set_volume(self, index: int, volume: float) -> None:
        validate_volume(volume, "Volume")
        self._volumes[index] = volume

    def cleanup(self) -> None:
        for proc in self._processes:
            try:
                proc.kill()
                proc.wait(timeout=1)
            except Exception:
                pass
        self._processes.clear()
        self._volumes.clear()
        self._finished.clear()
