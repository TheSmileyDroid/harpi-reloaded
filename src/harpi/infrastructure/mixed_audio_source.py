from typing import Any

import numpy as np
import discord

from harpi.domain.track import validate_volume

PCM_FRAME_SIZE: int = 960


class MixedAudioSource(discord.AudioSource):
    def __init__(
        self,
        processes: list[Any],
        volumes: list[float],
    ):
        self._processes = list(processes)
        self._volumes = list(volumes)
        for v in volumes:
            validate_volume(v, "Volume")

    def read(self) -> bytes:
        arrays = []
        i = 0
        while i < len(self._processes):
            proc = self._processes[i]
            stdout = proc.stdout
            if stdout is None:
                i += 1
                continue
            data = stdout.read(PCM_FRAME_SIZE)
            if not data or len(data) < PCM_FRAME_SIZE:
                i += 1
                continue
            arrays.append(
                np.frombuffer(data, dtype=np.int16).astype(np.float32)
                * self._volumes[i]
            )
            i += 1
        if not arrays:
            return b""
        mixed = np.clip(np.sum(arrays, axis=0), -32768, 32767).astype(np.int16)
        return mixed.tobytes()

    def add_source(self, process: Any, volume: float) -> None:
        self._processes.append(process)
        self._volumes.append(volume)

    def remove_source(self, index: int) -> Any:
        proc = self._processes.pop(index)
        self._volumes.pop(index)
        return proc

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
