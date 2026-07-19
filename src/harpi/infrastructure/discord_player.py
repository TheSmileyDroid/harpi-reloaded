import asyncio
import logging
import subprocess
import time
from collections.abc import Callable, Coroutine
from typing import Any


from harpi.application.ports.audio import AudioPlayerProtocol, AudioResolverProtocol
from harpi.domain.track_metadata import TrackMetadata
from harpi.domain.volume import validate_volume
from harpi.infrastructure.mixed_audio_source import MixedAudioSource

logger = logging.getLogger(__name__)


class DiscordPlayer(AudioPlayerProtocol):
    def __init__(
        self,
        resolver: AudioResolverProtocol,
        voice_client: Any = None,
    ):
        self._voice_client = voice_client
        self._resolver = resolver
        self._current: TrackMetadata | None = None
        self._start_time: float | None = None
        self._paused_position: float | None = None
        self._on_finish_callback: Callable[[], Coroutine[Any, Any, None]] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self.background_tracks: list[TrackMetadata] = []
        self.is_paused: bool = False
        self.volume: float = 1.0
        self.background_volume: float = 0.5
        self.duck_level: float = 1.0
        self._mixed_source: MixedAudioSource | None = None
        self._fg_proc: Any = None
        self._play_generation: int = 0

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
        self._play_generation += 1
        gen = self._play_generation
        self._current = track
        self._start_time = time.monotonic()
        self._paused_position = None
        self._on_finish_callback = on_finish
        self._loop = asyncio.get_event_loop()
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
                self._voice_client.play(source, after=lambda e: self._on_finish(e, gen))
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
        # Incrementar geração para invalidar callbacks `after` pendentes.
        self._play_generation += 1
        self._on_finish_callback = None
        self._voice_client.stop()
        if self._mixed_source is not None:
            self._mixed_source.cleanup()
            self._mixed_source = None
        self._fg_proc = None
        self._current = None
        self._start_time = None
        self._paused_position = None
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

    @staticmethod
    def _popen(args: list[str]) -> subprocess.Popen:
        return subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def _spawn_pcm_process(
        self,
        url: str,
        loop: bool = False,
        headers: dict | None = None,
        cookies: dict | None = None,
    ) -> Any:
        args = ["ffmpeg"]
        if loop:
            args += ["-stream_loop", "-1"]
        if headers:
            header_lines = [f"{k}: {v}" for k, v in headers.items()]
            args += ["-headers", "\r\n".join(header_lines) + "\r\n"]
        if cookies:
            cookie_lines = [f"{k}={v}" for k, v in cookies.items()]
            args += ["-cookies", "; ".join(cookie_lines)]
        args += [
            "-reconnect",
            "1",
            "-reconnect_streamed",
            "1",
            "-reconnect_delay_max",
            "5",
            "-i",
            url,
            *self._FFMPEG_PCM_ARGS,
        ]
        logger.info(
            "FFmpeg stream URL: %s...", url[:80] if isinstance(url, str) else "N/A"
        )
        logger.info(
            "FFmpeg cmd: %s (headers=%d, cookies=%d)",
            " ".join(args[:12]) + " ...",
            len(headers) if headers else 0,
            len(cookies) if cookies else 0,
        )
        return self._popen(args)

    async def _spawn_source_process(
        self, track: TrackMetadata, loop: bool = False
    ) -> Any:
        if self._resolver is None:
            raise RuntimeError("No resolver configured for stream resolution")

        # Extract fresh URL right before spawning to avoid expiration
        url = await self._resolver.resolve_stream(track)
        headers = {}
        cookies = {}
        if hasattr(self._resolver, "get_last_stream_headers"):
            resolver: Any = self._resolver
            headers = resolver.get_last_stream_headers()
            if hasattr(self._resolver, "get_last_stream_cookies"):
                cookies = resolver.get_last_stream_cookies()
        logger.debug(
            "Spawning FFmpeg for track: headers=%s cookies=%s",
            list(headers.keys()) if headers else "none",
            list(cookies.keys()) if cookies else "none",
        )
        proc = self._spawn_pcm_process(url, loop=loop, headers=headers, cookies=cookies)
        # Start stderr reader thread for debugging
        import threading
        def _read_stderr():
            for line in proc.stderr:
                logger.warning("FFmpeg stderr: %s", line.decode(errors="replace").strip())
        threading.Thread(target=_read_stderr, daemon=True).start()
        return proc

    @staticmethod
    def _kill_process(proc: Any) -> None:
        try:
            proc.kill()
            proc.wait(timeout=1)
        except Exception:
            pass

    def _effective_background_volume(self) -> float:
        # Enquanto há faixa principal tocando, os fundos abaixam pelo duck_level.
        if self._current is not None:
            return self.background_volume * self.duck_level
        return self.background_volume

    async def _build_mixed_source(self, track: TrackMetadata) -> MixedAudioSource:
        fg_proc = await self._spawn_source_process(track)
        self._fg_proc = fg_proc
        procs = [fg_proc]
        vols = [self.volume]
        for bg in self.background_tracks:
            try:
                procs.append(await self._spawn_source_process(bg, loop=True))
                vols.append(self._effective_background_volume())
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
        # Sem faixa principal, os fundos voltam ao volume cheio (des-ducking).
        self._apply_background_volume()
        # Com outras fontes ativas o stream não termina, então o `after` do
        # discord.py nunca dispararia: o avanço de fila é agendado daqui.
        # Sem fontes restantes, o `after` assume (via _on_finish).
        if (
            active_remaining > 0
            and self._on_finish_callback is not None
            and self._loop is not None
        ):
            asyncio.run_coroutine_threadsafe(self._on_finish_callback(), self._loop)

    async def add_background_source(self, track: TrackMetadata) -> None:
        self.background_tracks.append(track)
        if self._mixed_source is not None:
            try:
                proc = await self._spawn_source_process(track, loop=True)
                self._mixed_source.add_source(proc, self._effective_background_volume())
            except Exception:
                logger.warning("Failed to add background source for %s", track.link)

    def remove_background_source(self, index: int) -> TrackMetadata:
        removed = self.background_tracks.pop(index)
        if self._mixed_source is not None:
            # Slot 0 do mixer é a faixa principal; fundos começam no 1.
            proc = self._mixed_source.remove_source(index + 1)
            self._kill_process(proc)
        return removed

    def _on_finish(self, error: Exception | None, generation: int) -> None:
        if error:
            logger.error("Playback finished with error: %s", error)
        else:
            logger.info("Playback finished")
        # Ignorar callbacks de gerações anteriores (stale after callbacks).
        if generation != self._play_generation:
            logger.debug(
                "Ignoring stale on_finish callback (gen %d != %d)",
                generation,
                self._play_generation,
            )
            return
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
            self._mixed_source.set_volume(i, self._effective_background_volume())

    def set_background_volume(self, volume: float) -> None:
        validate_volume(volume, "Background volume")
        self.background_volume = volume
        self._apply_background_volume()
        logger.info("Background volume set to %s", volume)

    def set_ducking(self, duck_level: float) -> None:
        validate_volume(duck_level, "Duck level")
        self.duck_level = duck_level
        self._apply_background_volume()
        logger.info("Duck level set to %s", duck_level)

    def set_voice_client(self, voice_client: Any) -> None:
        self._voice_client = voice_client
        self.is_paused = False

    async def connect(self, channel) -> None:
        self._voice_client = await channel.connect()
        logger.info("Connected to voice channel %s", channel.name)
        self.is_paused = False


class DiscordPlayerFactory:
    def create_player(self, resolver: AudioResolverProtocol) -> AudioPlayerProtocol:
        return DiscordPlayer(resolver=resolver)
