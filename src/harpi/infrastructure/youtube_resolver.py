from pytubefix import YouTube
from harpi.domain.track import Track, Source
from harpi.application.ports.audio import AudioResolverProtocol


class YoutubeResolver(AudioResolverProtocol):
    async def resolve(self, link: str) -> Track:
        yt = YouTube(link)

        return Track(
            link=yt.watch_url,
            title=yt.title,
            duration=yt.length,
            source=Source.YOUTUBE,
            resolved=True,
        )
