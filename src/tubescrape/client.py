from __future__ import annotations

import logging

from tubescrape._http import HTTPClient
from tubescrape._utils import URLParser
from tubescrape.browse import YouTubeBrowse
from tubescrape.formatters import get_formatter
from tubescrape.models import (
    BrowseResult,
    ChannelPlaylistsResult,
    PlaylistResult,
    SearchResult,
    ShortsResult,
    Transcript,
    TranscriptListEntry,
)
from tubescrape.playlist import YouTubePlaylist
from tubescrape.search import YouTubeSearch
from tubescrape.transcript import YouTubeTranscript

logger = logging.getLogger('tubescrape')


class YouTube:
    """Main entry point for tubescrape.

    Provides a unified interface for searching videos, browsing channels,
    fetching transcripts, and scraping playlists from YouTube.
    No API key required.

    All methods accept both plain IDs and full YouTube URLs::

        yt = YouTube()

        # These all work the same:
        yt.get_transcript('dQw4w9WgXcQ')
        yt.get_transcript('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
        yt.get_transcript('https://youtu.be/dQw4w9WgXcQ')

        # Channel by ID, URL, or @handle:
        yt.get_channel_videos('UCmeeY9kzNswUpbYyJntb3Aw')
        yt.get_channel_videos('https://www.youtube.com/@lexfridman')
        yt.get_channel_videos('@lexfridman')

        # Playlist by ID or URL:
        yt.get_playlist('PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf')
        yt.get_playlist('https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf')

    Args:
        proxy: Single proxy URL (e.g. 'http://user:pass@host:port').
        proxies: List of proxy URLs for rotation.
        timeout: Request timeout in seconds.
        max_retries: Maximum retry attempts on transient failures.
        cookies: Additional cookies to include in all requests.
        transcript_proxy: Proxy URL for transcript requests (residential recommended).
        transcript_proxies: List of proxy URLs for transcript rotation.
            YouTube's player/caption endpoints are stricter about datacenter IPs.
            Use residential proxies here while using cheaper datacenter proxies
            for search/browse via the main proxy/proxies parameters.
    """

    def __init__(
        self,
        proxy: str | None = None,
        proxies: list[str] | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        cookies: dict[str, str] | None = None,
        transcript_proxy: str | None = None,
        transcript_proxies: list[str] | None = None,
    ):
        self._http = HTTPClient(
            proxy=proxy,
            proxies=proxies,
            timeout=timeout,
            max_retries=max_retries,
            cookies=cookies,
            transcript_proxy=transcript_proxy,
            transcript_proxies=transcript_proxies,
        )
        self._search = YouTubeSearch(self._http)
        self._browse = YouTubeBrowse(self._http)
        self._transcript = YouTubeTranscript(self._http)
        self._playlist = YouTubePlaylist(self._http)

    # ── Search ──

    def search(
        self,
        query: str,
        max_results: int = 20,
        params: str = '',
        sort_by: str | None = None,
        upload_date: str | None = None,
        type: str | None = None,
        duration: str | None = None,
        features: str | list[str] | None = None,
    ) -> SearchResult:
        """Search YouTube videos.

        Args:
            query: Search query string.
            max_results: Maximum number of results (1-50).
            params: Raw protobuf-encoded search filter (base64 string).
                    Ignored if any named filter is provided.
            sort_by: Sort order — 'relevance', 'upload_date', 'view_count', 'rating'.
            upload_date: Time filter — 'last_hour', 'today', 'this_week',
                         'this_month', 'this_year'.
            type: Content type — 'video', 'channel', 'playlist', 'movie'.
            duration: Duration filter — 'short' (<4min), 'medium' (4-20min),
                      'long' (>20min).
            features: Feature filter(s) — 'live', '4k', 'hd', 'subtitles', 'cc',
                      'creative_commons', '360', 'vr180', '3d', 'hdr'.
                      Can be a single string or list of strings.

        Returns:
            SearchResult containing matched videos.

        Examples::

            yt.search('python tutorial')
            yt.search('podcast', type='video', duration='long')
            yt.search('news', upload_date='today', sort_by='view_count')
            yt.search('music', features=['4k', 'hdr'])
        """
        return self._search.search(
            query,
            max_results=max_results,
            params=params,
            sort_by=sort_by,
            upload_date=upload_date,
            type=type,
            duration=duration,
            features=features,
        )

    async def asearch(
        self,
        query: str,
        max_results: int = 20,
        params: str = '',
        sort_by: str | None = None,
        upload_date: str | None = None,
        type: str | None = None,
        duration: str | None = None,
        features: str | list[str] | None = None,
    ) -> SearchResult:
        """Async version of search."""
        return await self._search.asearch(
            query,
            max_results=max_results,
            params=params,
            sort_by=sort_by,
            upload_date=upload_date,
            type=type,
            duration=duration,
            features=features,
        )

    # ── Channel Browse ──

    def get_channel_videos(
        self,
        channel: str,
        max_results: int = 30,
    ) -> BrowseResult:
        """Get videos from a YouTube channel.

        Accepts a channel ID, full URL, or @handle::

            yt.get_channel_videos('UCmeeY9kzNswUpbYyJntb3Aw')
            yt.get_channel_videos('https://www.youtube.com/channel/UCmeeY9kzNswUpbYyJntb3Aw')
            yt.get_channel_videos('https://www.youtube.com/@lexfridman')
            yt.get_channel_videos('@lexfridman')

        Args:
            channel: Channel ID (UC...), @handle, or full YouTube channel URL.
            max_results: Maximum number of videos. Use 0 for all.

        Returns:
            BrowseResult containing the channel's videos.
        """
        channel_id = self._resolve_channel(channel)
        return self._browse.get_channel_videos(channel_id, max_results=max_results)

    async def aget_channel_videos(
        self,
        channel: str,
        max_results: int = 30,
    ) -> BrowseResult:
        """Async version of get_channel_videos."""
        channel_id = await self._aresolve_channel(channel)
        return await self._browse.aget_channel_videos(
            channel_id, max_results=max_results,
        )

    # ── Channel Shorts ──

    def get_channel_shorts(self, channel: str) -> ShortsResult:
        """Get Shorts from a YouTube channel's Shorts tab.

        Accepts a channel ID, full URL, or @handle.

        Args:
            channel: Channel ID (UC...), @handle, or full YouTube channel URL.

        Returns:
            ShortsResult containing the channel's shorts.
        """
        channel_id = self._resolve_channel(channel)
        return self._browse.get_channel_shorts(channel_id)

    async def aget_channel_shorts(self, channel: str) -> ShortsResult:
        """Async version of get_channel_shorts."""
        channel_id = await self._aresolve_channel(channel)
        return await self._browse.aget_channel_shorts(channel_id)

    # ── Channel Playlists ──

    def get_channel_playlists(self, channel: str) -> ChannelPlaylistsResult:
        """Get playlists from a YouTube channel's Playlists tab.

        Accepts a channel ID, full URL, or @handle.

        Args:
            channel: Channel ID (UC...), @handle, or full YouTube channel URL.

        Returns:
            ChannelPlaylistsResult containing the channel's playlists.
        """
        channel_id = self._resolve_channel(channel)
        return self._browse.get_channel_playlists(channel_id)

    async def aget_channel_playlists(self, channel: str) -> ChannelPlaylistsResult:
        """Async version of get_channel_playlists."""
        channel_id = await self._aresolve_channel(channel)
        return await self._browse.aget_channel_playlists(channel_id)

    # ── Channel Search ──

    def search_channel(
        self,
        channel: str,
        query: str,
        max_results: int = 0,
    ) -> SearchResult:
        """Search within a YouTube channel's videos.

        Accepts a channel ID, full URL, or @handle.

        Args:
            channel: Channel ID (UC...), @handle, or full YouTube channel URL.
            query: Search query string.
            max_results: Maximum number of results. Use 0 for all (default).

        Returns:
            SearchResult containing matched videos from the channel.
        """
        channel_id = self._resolve_channel(channel)
        result = self._browse.search_channel(channel_id, query)
        if max_results > 0 and len(result.videos) > max_results:
            result = SearchResult(query=result.query, videos=result.videos[:max_results])
        return result

    async def asearch_channel(
        self,
        channel: str,
        query: str,
        max_results: int = 0,
    ) -> SearchResult:
        """Async version of search_channel."""
        channel_id = await self._aresolve_channel(channel)
        result = await self._browse.asearch_channel(channel_id, query)
        if max_results > 0 and len(result.videos) > max_results:
            result = SearchResult(query=result.query, videos=result.videos[:max_results])
        return result

    # ── Playlists ──

    def get_playlist(
        self,
        playlist: str,
        max_results: int = 0,
    ) -> PlaylistResult:
        """Fetch videos from a YouTube playlist.

        Accepts a playlist ID or full URL::

            yt.get_playlist('PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf')
            yt.get_playlist('https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf')

        Args:
            playlist: Playlist ID or full YouTube playlist URL.
            max_results: Maximum number of videos. Use 0 for all.

        Returns:
            PlaylistResult with playlist metadata and videos.
        """
        playlist_id = URLParser.extract_playlist_id(playlist)
        return self._playlist.get_playlist(playlist_id, max_results=max_results)

    async def aget_playlist(
        self,
        playlist: str,
        max_results: int = 0,
    ) -> PlaylistResult:
        """Async version of get_playlist."""
        playlist_id = URLParser.extract_playlist_id(playlist)
        return await self._playlist.aget_playlist(
            playlist_id, max_results=max_results,
        )

    # ── Transcripts ──

    def get_transcript(
        self,
        video: str,
        languages: list[str] | None = None,
        timestamps: bool = True,
        translate_to: str | None = None,
    ) -> Transcript:
        """Fetch transcript for a video.

        Accepts a video ID or full URL::

            yt.get_transcript('dQw4w9WgXcQ')
            yt.get_transcript('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
            yt.get_transcript('https://youtu.be/dQw4w9WgXcQ')

        Args:
            video: YouTube video ID or URL.
            languages: Preferred language codes in priority order. Defaults to ['en'].
            timestamps: If True (default), return segments with timing info.
                        If False, return plain text without timestamps.
            translate_to: Target language code for translation (e.g. 'es', 'fr').
                          Translates the transcript if the language is available.

        Returns:
            Transcript object with segments and metadata.

        Raises:
            TranslationNotAvailableError: If translate_to language is not available.
        """
        video_id = URLParser.extract_video_id(video)
        return self._transcript.get_transcript(
            video_id,
            languages=languages,
            timestamps=timestamps,
            translate_to=translate_to,
        )

    async def aget_transcript(
        self,
        video: str,
        languages: list[str] | None = None,
        timestamps: bool = True,
        translate_to: str | None = None,
    ) -> Transcript:
        """Async version of get_transcript."""
        video_id = URLParser.extract_video_id(video)
        return await self._transcript.aget_transcript(
            video_id,
            languages=languages,
            timestamps=timestamps,
            translate_to=translate_to,
        )

    def list_transcripts(self, video: str) -> list[TranscriptListEntry]:
        """List available transcripts for a video.

        Accepts a video ID or full URL.

        Args:
            video: YouTube video ID or URL.

        Returns:
            List of TranscriptListEntry with language and availability info.
        """
        video_id = URLParser.extract_video_id(video)
        return self._transcript.list_transcripts(video_id)

    async def alist_transcripts(self, video: str) -> list[TranscriptListEntry]:
        """Async version of list_transcripts."""
        video_id = URLParser.extract_video_id(video)
        return await self._transcript.alist_transcripts(video_id)

    # ── Formatting ──

    @staticmethod
    def format_transcript(transcript: Transcript, fmt: str = 'text') -> str:
        """Format a transcript into a string.

        Args:
            transcript: Transcript object to format.
            fmt: Output format ('text', 'json', 'srt', 'vtt', 'webvtt').

        Returns:
            Formatted transcript string.
        """
        formatter = get_formatter(fmt)
        return formatter.format(transcript)

    # ── URL Parsing ──

    @staticmethod
    def extract_video_id(url_or_id: str) -> str:
        """Extract a video ID from a URL or return the ID if already plain.

        Supports youtube.com/watch, youtu.be, /embed/, /shorts/, /live/ URLs.

        Args:
            url_or_id: YouTube video URL or plain 11-character video ID.

        Returns:
            11-character video ID string.

        Raises:
            ValueError: If the input cannot be parsed as a video ID.
        """
        return URLParser.extract_video_id(url_or_id)

    @staticmethod
    def extract_channel_id(url_or_id: str) -> str | None:
        """Extract a channel identifier from a URL, @handle, or plain ID.

        Note: For @handles and vanity URLs, the returned value must be resolved
        via get_channel_videos() which handles resolution automatically.

        Args:
            url_or_id: YouTube channel URL, @handle, or plain channel ID.

        Returns:
            Channel ID (UC...) or handle string for resolution.

        Raises:
            ValueError: If the input cannot be parsed.
        """
        return URLParser.extract_channel_id(url_or_id)

    @staticmethod
    def extract_playlist_id(url_or_id: str) -> str:
        """Extract a playlist ID from a URL or return the ID if already plain.

        Args:
            url_or_id: YouTube playlist URL or plain playlist ID.

        Returns:
            Playlist ID string.

        Raises:
            ValueError: If the input cannot be parsed as a playlist ID.
        """
        return URLParser.extract_playlist_id(url_or_id)

    # ── Internal ──

    def _resolve_channel(self, channel: str) -> str:
        """Resolve any channel input (ID, URL, @handle) to a channel ID."""
        resolved = URLParser.extract_channel_id(channel)
        if resolved and resolved.startswith('UC') and len(resolved) == 24:
            return resolved
        # Needs resolution (@handle, /c/, /user/)
        return self._browse.resolve_channel_id(resolved or channel)

    async def _aresolve_channel(self, channel: str) -> str:
        """Async version of _resolve_channel."""
        resolved = URLParser.extract_channel_id(channel)
        if resolved and resolved.startswith('UC') and len(resolved) == 24:
            return resolved
        return await self._browse.aresolve_channel_id(resolved or channel)

    # ── Lifecycle ──

    def close(self) -> None:
        """Close HTTP connections."""
        self._http.close()

    async def aclose(self) -> None:
        """Close async HTTP connections."""
        await self._http.aclose()

    def __enter__(self) -> YouTube:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    async def __aenter__(self) -> YouTube:
        return self

    async def __aexit__(self, *args) -> None:
        await self.aclose()

    def __repr__(self) -> str:
        return f'YouTube(proxy={self._http._proxy!r})'
