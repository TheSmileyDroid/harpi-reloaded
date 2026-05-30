from pytubefix.async_youtube import AsyncYouTube
from harpi.domain.track import Track, Source
from harpi.application.ports.audio import AudioResolverProtocol


class YoutubeResolver(AudioResolverProtocol):
    async def resolve(self, link: str) -> Track:
        yt = AsyncYouTube(link)

        return Track(
            link=yt.watch_url,
            title=await yt.title(),
            duration=await yt.length(),
            source=Source.YOUTUBE,
            resolved=True,
        )
