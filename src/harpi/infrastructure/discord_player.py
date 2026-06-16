import asyncio
import logging
import subprocess
import time
from collections.abc import Callable, Coroutine
from typing import Any


from pytubefix.async_youtube import AsyncYouTube

from harpi.application.ports.audio import AudioPlayerProtocol
from harpi.domain.track import Track
from harpi.infrastructure.mixed_audio_source import MixedAudioSource

logger = logging.getLogger(__name__)


class DiscordPlayer(AudioPlayerProtocol):
    def __init__(
        self,
        voice_client: Any = None,
        source_factory: Callable[[Track], Coroutine[Any, Any, Any]] | None = None,
    ):
        self._voice_client = voice_client
        self._source_factory = source_factory or self._default_source_factory
        self._current: Track | None = None
        self._start_time: float | None = None
        self._paused_position: float | None = None
        self._on_finish_callback: Callable[[], Coroutine[Any, Any, None]] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._duck_level: float = 0.2
        self._saved_background_volume: float | None = None
        self.background_tracks: list[Track] = []
        self.is_paused: bool = False
        self.is_stopped: bool = False
        self.volume: float = 1.0
        self.background_volume: float = 0.5
        self.is_ducking: bool = False
        self._mixed_source: MixedAudioSource | None = None

    @property
    def playing(self) -> Track | None:
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
        track: Track,
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
            source = await self._build_mixed_source(track)
            if self._mixed_source is None:
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
        self._voice_client.stop()
        if self._mixed_source is not None:
            self._mixed_source.cleanup()
            self._mixed_source = None
        self._current = None
        self._start_time = None
        self._paused_position = None
        self.is_stopped = True
        self.is_paused = False

    async def _build_mixed_source(self, track: Track) -> MixedAudioSource:
        fg_url = await self._resolve_url(track)
        fg_proc = subprocess.Popen(
            ["ffmpeg", "-i", fg_url, "-f", "s16le", "-ar", "48000", "-ac", "2", "pipe:1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        procs = [fg_proc]
        vols = [self.volume]
        for bg in self.background_tracks:
            try:
                url = await self._resolve_url(bg)
                proc = subprocess.Popen(
                    ["ffmpeg", "-i", url, "-f", "s16le", "-ar", "48000", "-ac", "2", "pipe:1"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
                procs.append(proc)
                vols.append(self.background_volume)
            except Exception:
                logger.warning("Failed to resolve background track %s", bg.link)
        source = MixedAudioSource(procs, vols)
        self._mixed_source = source
        return source

    @staticmethod
    async def _resolve_url(track: Track) -> str:
        yt = AsyncYouTube(track.link)
        streams = await yt.streams()
        stream = streams.get_audio_only()
        if stream is None:
            raise ValueError(f"No audio stream available for {track.link}")
        return stream.url

    async def add_background_source(self, track: Track) -> None:
        self.background_tracks.append(track)
        if self._mixed_source is not None:
            try:
                url = await self._resolve_url(track)
                proc = subprocess.Popen(
                    ["ffmpeg", "-i", url, "-f", "s16le", "-ar", "48000", "-ac", "2", "pipe:1"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
                self._mixed_source.add_source(proc, self.background_volume)
            except Exception:
                logger.warning("Failed to add background source for %s", track.link)

    def remove_background_source(self, index: int) -> Track:
        removed = self.background_tracks.pop(index)
        if self._mixed_source is not None:
            proc = self._mixed_source.remove_source(index)
            try:
                proc.kill()
                proc.wait(timeout=1)
            except Exception:
                pass
        return removed

    def _on_finish(self, error: Exception | None) -> None:
        if error:
            logger.error("Playback finished with error: %s", error)
        else:
            logger.info("Playback finished")
        self._current = None
        self._start_time = None
        if self._on_finish_callback is not None and self._loop is not None:
            asyncio.run_coroutine_threadsafe(self._on_finish_callback(), self._loop)

    def set_volume(self, volume: float) -> None:
        if not 0.0 <= volume <= 1.0:
            raise ValueError(f"Volume must be between 0.0 and 1.0, got {volume}")
        self.volume = volume
        logger.info("Volume set to %s", volume)

    def set_background_volume(self, volume: float) -> None:
        if not 0.0 <= volume <= 1.0:
            raise ValueError(
                f"Background volume must be between 0.0 and 1.0, got {volume}"
            )
        self.background_volume = volume
        logger.info("Background volume set to %s", volume)

    def set_ducking(self, duck_level: float) -> None:
        if not 0.0 <= duck_level <= 1.0:
            raise ValueError(
                f"Duck level must be between 0.0 and 1.0, got {duck_level}"
            )
        self._duck_level = duck_level
        logger.info("Duck level set to %s", duck_level)

    async def duck(self) -> None:
        if self.is_ducking:
            return
        self._saved_background_volume = self.background_volume
        self.background_volume = self._duck_level
        self.is_ducking = True
        logger.info("Ducking: background volume -> %s", self._duck_level)

    async def unduck(self) -> None:
        if not self.is_ducking:
            return
        if self._saved_background_volume is not None:
            self.background_volume = self._saved_background_volume
            self._saved_background_volume = None
        self.is_ducking = False
        logger.info("Unducking: background volume restored to %s", self.background_volume)

    def set_voice_client(self, vc: Any) -> None:
        self._voice_client = vc
        self.is_stopped = False
        self.is_paused = False

    async def connect(self, channel) -> None:
        self._voice_client = await channel.connect()
        logger.info("Connected to voice channel %s", channel.name)
        self.is_stopped = True
        self.is_paused = False

    @staticmethod
    async def _default_source_factory(track: Track) -> Any:
        import discord

        url = await DiscordPlayer._resolve_url(track)
        return discord.FFmpegPCMAudio(
            url,
            before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        )
