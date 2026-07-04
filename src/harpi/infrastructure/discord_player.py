import asyncio
import logging
import subprocess
import time
from collections.abc import Callable, Coroutine
from typing import Any


from pytubefix.async_youtube import AsyncYouTube

from harpi.application.ports.audio import AudioPlayerProtocol
from harpi.domain.track_metadata import TrackMetadata
from harpi.domain.volume import validate_volume
from harpi.infrastructure.mixed_audio_source import MixedAudioSource

logger = logging.getLogger(__name__)


class DiscordPlayer(AudioPlayerProtocol):
    def __init__(
        self,
        voice_client: Any = None,
    ):
        self._voice_client = voice_client
        self._current: TrackMetadata | None = None
        self._start_time: float | None = None
        self._paused_position: float | None = None
        self._on_finish_callback: Callable[[], Coroutine[Any, Any, None]] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._duck_level: float = 0.2
        self._saved_background_volume: float | None = None
        self.background_tracks: list[TrackMetadata] = []
        self.is_paused: bool = False
        self.is_stopped: bool = False
        self.volume: float = 1.0
        self.background_volume: float = 0.5
        self.is_ducking: bool = False
        self._mixed_source: MixedAudioSource | None = None
        self._fg_proc: Any = None

    @property
    def playing(self) -> TrackMetadata | None:
        return self._current

    @property
    def is_connected(self) -> bool:
        return self._voice_client is not None

    @property
    def position(self) -> float | None:
        if self._current is None:
            return None
        if self.is_paused:
            return self._paused_position
        if self._start_time is None:
            return None
        return time.monotonic() - self._start_time

    def _check_connected(self) -> None:
        if self._voice_client is None:
            raise RuntimeError("Not connected to a voice channel")

    async def play(
        self,
        track: TrackMetadata,
        on_finish: Callable[[], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        self._check_connected()
        self._current = track
        self._start_time = time.monotonic()
        self._paused_position = None
        self._on_finish_callback = on_finish
        self._loop = asyncio.get_event_loop()
        self.is_stopped = False
        self.is_paused = False
        logger.info("Playing %s (%s)", track.title, track.link)
        try:
            if (
                self._mixed_source is not None
                and self._fg_proc is not None
                and self._voice_client.is_playing()
            ):
                # O mixer segue vivo tocando os fundos: troca só o slot 0
                # (faixa principal) em vez de recriar tudo.
                new_proc = await self._spawn_source_process(track)
                old = self._mixed_source.replace_source(0, new_proc, self.volume)
                self._fg_proc = new_proc
                self._kill_process(old)
            else:
                if self._mixed_source is not None:
                    self._mixed_source.cleanup()
                    self._mixed_source = None
                source = await self._build_mixed_source(track)
                self._mixed_source = source
                self._voice_client.play(source, after=lambda e: self._on_finish(e))
        except Exception:
            logger.exception("Failed to create audio source for %s", track.link)
            raise

    async def pause(self) -> None:
        self._check_connected()
        logger.info("Pausing playback")
        if self._start_time is not None and not self.is_paused:
            self._paused_position = time.monotonic() - self._start_time
        self._voice_client.pause()
        self.is_paused = True

    async def resume(self) -> None:
        self._check_connected()
        logger.info("Resuming playback")
        if self._paused_position is not None:
            self._start_time = time.monotonic() - self._paused_position
            self._paused_position = None
        self._voice_client.resume()
        self.is_paused = False

    async def stop(self) -> None:
        self._check_connected()
        logger.info("Stopping playback")
        # Parada manual não é fim de faixa: sem callback de avanço.
        self._on_finish_callback = None
        self._voice_client.stop()
        if self._mixed_source is not None:
            self._mixed_source.cleanup()
            self._mixed_source = None
        self._fg_proc = None
        self._current = None
        self._start_time = None
        self._paused_position = None
        self.is_stopped = True
        self.is_paused = False

    _FFMPEG_PCM_ARGS = [
        "-f",
        "s16le",
        "-ar",
        "48000",
        "-ac",
        "2",
        "pipe:1",
    ]

    def _spawn_pcm_process(self, url: str) -> subprocess.Popen:
        return subprocess.Popen(
            [
                "ffmpeg",
                "-reconnect",
                "1",
                "-reconnect_streamed",
                "1",
                "-reconnect_delay_max",
                "5",
                "-i",
                url,
                *self._FFMPEG_PCM_ARGS,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

    async def _spawn_source_process(self, track: TrackMetadata) -> Any:
        url = await self._resolve_url(track)
        return self._spawn_pcm_process(url)

    @staticmethod
    def _kill_process(proc: Any) -> None:
        try:
            proc.kill()
            proc.wait(timeout=1)
        except Exception:
            pass

    async def _build_mixed_source(self, track: TrackMetadata) -> MixedAudioSource:
        fg_proc = await self._spawn_source_process(track)
        self._fg_proc = fg_proc
        procs = [fg_proc]
        vols = [self.volume]
        for bg in self.background_tracks:
            try:
                procs.append(await self._spawn_source_process(bg))
                vols.append(self.background_volume)
            except Exception:
                logger.warning("Failed to resolve background track %s", bg.link)
        return MixedAudioSource(
            procs, vols, on_source_finished=self._handle_source_finished
        )

    def _handle_source_finished(self, proc: Any, active_remaining: int) -> None:
        """Chamado pela thread de áudio quando uma fonte do mixer termina."""
        if proc is not self._fg_proc:
            return
        logger.info("Foreground track finished")
        self._current = None
        self._start_time = None
        self._paused_position = None
        # Com outras fontes ativas o stream não termina, então o `after` do
        # discord.py nunca dispararia: o avanço de fila é agendado daqui.
        # Sem fontes restantes, o `after` assume (via _on_finish).
        if (
            active_remaining > 0
            and self._on_finish_callback is not None
            and self._loop is not None
        ):
            asyncio.run_coroutine_threadsafe(self._on_finish_callback(), self._loop)

    @staticmethod
    async def _resolve_url(track: TrackMetadata) -> str:
        # WEB retorna URLs SABR que o FFmpeg não consegue abrir; ANDROID_VR
        # serve stream direto sem exigir PO Token.
        yt = AsyncYouTube(track.link, "ANDROID_VR")
        streams = await yt.streams()
        stream = streams.get_audio_only()
        if stream is None:
            raise ValueError(f"No audio stream available for {track.link}")
        return stream.url

    async def add_background_source(self, track: TrackMetadata) -> None:
        self.background_tracks.append(track)
        if self._mixed_source is not None:
            try:
                proc = await self._spawn_source_process(track)
                self._mixed_source.add_source(proc, self.background_volume)
            except Exception:
                logger.warning("Failed to add background source for %s", track.link)

    def remove_background_source(self, index: int) -> TrackMetadata:
        removed = self.background_tracks.pop(index)
        if self._mixed_source is not None:
            # Slot 0 do mixer é a faixa principal; fundos começam no 1.
            proc = self._mixed_source.remove_source(index + 1)
            self._kill_process(proc)
        return removed

    def _on_finish(self, error: Exception | None) -> None:
        if error:
            logger.error("Playback finished with error: %s", error)
        else:
            logger.info("Playback finished")
        if self._mixed_source is not None:
            self._mixed_source.cleanup()
            self._mixed_source = None
        self._fg_proc = None
        self._current = None
        self._start_time = None
        if self._on_finish_callback is not None and self._loop is not None:
            asyncio.run_coroutine_threadsafe(self._on_finish_callback(), self._loop)

    def set_volume(self, volume: float) -> None:
        validate_volume(volume, "Volume")
        self.volume = volume
        if self._mixed_source is not None and self._fg_proc is not None:
            self._mixed_source.set_volume(0, volume)
        logger.info("Volume set to %s", volume)

    def _apply_background_volume(self) -> None:
        if self._mixed_source is None or self._fg_proc is None:
            return
        for i in range(1, self._mixed_source.source_count):
            self._mixed_source.set_volume(i, self.background_volume)

    def set_background_volume(self, volume: float) -> None:
        validate_volume(volume, "Background volume")
        self.background_volume = volume
        self._apply_background_volume()
        logger.info("Background volume set to %s", volume)

    def set_ducking(self, duck_level: float) -> None:
        validate_volume(duck_level, "Duck level")
        self._duck_level = duck_level
        logger.info("Duck level set to %s", duck_level)

    async def duck(self) -> None:
        if self.is_ducking:
            return
        self._saved_background_volume = self.background_volume
        self.background_volume = self._duck_level
        self.is_ducking = True
        self._apply_background_volume()
        logger.info("Ducking: background volume -> %s", self._duck_level)

    async def unduck(self) -> None:
        if not self.is_ducking:
            return
        if self._saved_background_volume is not None:
            self.background_volume = self._saved_background_volume
            self._saved_background_volume = None
        self.is_ducking = False
        self._apply_background_volume()
        logger.info(
            "Unducking: background volume restored to %s", self.background_volume
        )

    def set_voice_client(self, vc: Any) -> None:
        self._voice_client = vc
        self.is_stopped = False
        self.is_paused = False

    async def connect(self, channel) -> None:
        self._voice_client = await channel.connect()
        logger.info("Connected to voice channel %s", channel.name)
        self.is_stopped = True
        self.is_paused = False
