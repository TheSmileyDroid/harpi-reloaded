import asyncio
import logging
import time
from collections.abc import Callable, Coroutine
from typing import Any


from pytubefix.async_youtube import AsyncYouTube

from harpi.application.ports.audio import AudioPlayerProtocol
from harpi.domain.track import Track

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
        self.background_tracks: list[Track] = []
        self.is_paused: bool = False
        self.is_stopped: bool = False

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
            source = await self._source_factory(track)
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
        self._current = None
        self._start_time = None
        self._paused_position = None
        self.is_stopped = True
        self.is_paused = False

    def _on_finish(self, error: Exception | None) -> None:
        if error:
            logger.error("Playback finished with error: %s", error)
        else:
            logger.info("Playback finished")
        self._current = None
        self._start_time = None
        if self._on_finish_callback is not None and self._loop is not None:
            asyncio.run_coroutine_threadsafe(self._on_finish_callback(), self._loop)

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
        yt = AsyncYouTube(track.link)
        streams = await yt.streams()
        stream = streams.get_audio_only()
        if stream is None:
            raise ValueError(f"No audio stream available for {track.link}")
        import discord

        return discord.FFmpegPCMAudio(
            stream.url,
            before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        )
