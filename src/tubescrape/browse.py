from __future__ import annotations

import dataclasses
import logging
import re

from tubescrape._http import HTTPClient
from tubescrape._innertube import InnerTube
from tubescrape._parsers import ResponseParser
from tubescrape.exceptions import ChannelNotFoundError
from tubescrape.models import (
    BrowseResult,
    ChannelPlaylistsResult,
    SearchResult,
    ShortsResult,
    VideoResult,
)

logger = logging.getLogger('tubescrape.browse')


class YouTubeBrowse:
    """Browse a YouTube channel's Videos tab via the InnerTube browse API.

    Returns videos in upload-date order (newest first).

    Args:
        http_client: HTTPClient instance for making requests.
    """

    def __init__(self, http_client: HTTPClient):
        self._http = http_client

    def resolve_channel_id(self, handle_or_vanity: str) -> str:
        """Resolve a @handle, /c/Name, or /user/Name to a channel ID.

        Fetches the YouTube page and extracts the canonical channel ID.

        Args:
            handle_or_vanity: A string like '@lexfridman', '/c/ChannelName',
                              or '/user/Username'.

        Returns:
            Channel ID string (UC...).

        Raises:
            ChannelNotFoundError: If the channel cannot be found.
        """
        if handle_or_vanity.startswith('/c/') or handle_or_vanity.startswith('/user/'):
            url = f'https://www.youtube.com{handle_or_vanity}'
        elif handle_or_vanity.startswith('@'):
            url = f'https://www.youtube.com/{handle_or_vanity}'
        else:
            raise ChannelNotFoundError(handle_or_vanity)

        return self._resolve_from_page(url, handle_or_vanity)

    async def aresolve_channel_id(self, handle_or_vanity: str) -> str:
        """Async version of resolve_channel_id."""
        if handle_or_vanity.startswith('/c/') or handle_or_vanity.startswith('/user/'):
            url = f'https://www.youtube.com{handle_or_vanity}'
        elif handle_or_vanity.startswith('@'):
            url = f'https://www.youtube.com/{handle_or_vanity}'
        else:
            raise ChannelNotFoundError(handle_or_vanity)

        return await self._aresolve_from_page(url, handle_or_vanity)

    def _resolve_from_page(self, url: str, original: str) -> str:
        """Fetch a YouTube page and extract the channel ID from meta tags."""
        response = self._http.get(url)
        channel_id = self._extract_channel_id_from_html(response.text)
        if not channel_id:
            raise ChannelNotFoundError(original)
        logger.info('Resolved %r to channel ID: %s', original, channel_id)
        return channel_id

    async def _aresolve_from_page(self, url: str, original: str) -> str:
        """Async version of _resolve_from_page."""
        response = await self._http.aget(url)
        channel_id = self._extract_channel_id_from_html(response.text)
        if not channel_id:
            raise ChannelNotFoundError(original)
        logger.info('Resolved %r to channel ID: %s', original, channel_id)
        return channel_id

    @staticmethod
    def _extract_channel_id_from_html(html: str) -> str | None:
        """Extract channel ID from YouTube page HTML.

        Looks for patterns like:
            <meta itemprop="channelId" content="UCxxxxxx">
            "channelId":"UCxxxxxx"
            "externalId":"UCxxxxxx"
        """
        # Meta tag (most reliable)
        match = re.search(
            r'<meta\s+itemprop="channelId"\s+content="(UC[A-Za-z0-9_-]{22})"',
            html,
        )
        if match:
            return match.group(1)

        # JSON in page source
        match = re.search(r'"channelId"\s*:\s*"(UC[A-Za-z0-9_-]{22})"', html)
        if match:
            return match.group(1)

        match = re.search(r'"externalId"\s*:\s*"(UC[A-Za-z0-9_-]{22})"', html)
        if match:
            return match.group(1)

        return None

    def get_channel_videos(
        self,
        channel_id: str,
        max_results: int = 30,
    ) -> BrowseResult:
        """Get videos from a channel's Videos tab.

        Args:
            channel_id: YouTube channel ID (e.g. 'UCmeeY9kzNswUpbYyJntb3Aw').
            max_results: Maximum number of videos to return. Use 0 for all.

        Returns:
            BrowseResult containing the channel's videos.
        """
        all_videos: list[VideoResult] = []

        payload = InnerTube.build_browse_payload(channel_id)
        response = self._http.post(
            InnerTube.BROWSE_URL,
            json=payload,
            params={'prettyPrint': 'false'},
        )
        data = response.json()

        channel_name = ResponseParser.extract_channel_name(data)
        videos, continuation = ResponseParser.parse_browse_first_page(data, channel_id)
        all_videos.extend(videos)
        page = 1
        logger.info(
            '[page %d] %d videos fetched (total: %d)',
            page, len(videos), len(all_videos),
        )

        while continuation:
            if max_results > 0 and len(all_videos) >= max_results:
                all_videos = all_videos[:max_results]
                break

            page += 1
            payload = InnerTube.build_browse_payload(channel_id, continuation=continuation)

            try:
                response = self._http.post(
                    InnerTube.BROWSE_URL,
                    json=payload,
                    params={'prettyPrint': 'false'},
                )
                data = response.json()
            except Exception as exc:
                logger.warning('[page %d] Browse continuation failed: %s', page, exc)
                break

            videos, continuation = ResponseParser.parse_browse_continuation(data)
            if not videos:
                logger.info('[page %d] No more videos, stopping', page)
                break

            all_videos.extend(videos)
            logger.info(
                '[page %d] %d videos fetched (total: %d)',
                page, len(videos), len(all_videos),
            )

        if max_results > 0:
            all_videos = all_videos[:max_results]

        logger.info(
            'Browse complete: %d pages, %d total videos', page, len(all_videos),
        )

        # Fill in channel name/id on videos where missing (lockupViewModel
        # format does not include per-video channel info).
        if channel_name or channel_id:
            all_videos = [
                dataclasses.replace(
                    v,
                    channel=v.channel or channel_name or '',
                    channel_id=v.channel_id or channel_id,
                ) if not v.channel or not v.channel_id else v
                for v in all_videos
            ]

        return BrowseResult(
            channel_id=channel_id, channel=channel_name, videos=all_videos,
        )

    # ── Shorts ──

    def get_channel_shorts(self, channel_id: str) -> ShortsResult:
        """Get Shorts from a channel's Shorts tab.

        Args:
            channel_id: YouTube channel ID (UC...).

        Returns:
            ShortsResult containing the channel's shorts.
        """
        payload = InnerTube.build_shorts_payload(channel_id)
        response = self._http.post(
            InnerTube.BROWSE_URL, json=payload,
            params={'prettyPrint': 'false'},
        )
        data = response.json()
        result = ResponseParser.parse_shorts_tab(data, channel_id)
        logger.info('Shorts: %d shorts fetched for %s', len(result.shorts), channel_id)
        return result

    async def aget_channel_shorts(self, channel_id: str) -> ShortsResult:
        """Async version of get_channel_shorts."""
        payload = InnerTube.build_shorts_payload(channel_id)
        response = await self._http.apost(
            InnerTube.BROWSE_URL, json=payload,
            params={'prettyPrint': 'false'},
        )
        data = response.json()
        return ResponseParser.parse_shorts_tab(data, channel_id)

    # ── Channel Playlists ──

    def get_channel_playlists(self, channel_id: str) -> ChannelPlaylistsResult:
        """Get playlists from a channel's Playlists tab.

        Args:
            channel_id: YouTube channel ID (UC...).

        Returns:
            ChannelPlaylistsResult containing the channel's playlists.
        """
        payload = InnerTube.build_playlists_tab_payload(channel_id)
        response = self._http.post(
            InnerTube.BROWSE_URL, json=payload,
            params={'prettyPrint': 'false'},
        )
        data = response.json()
        result = ResponseParser.parse_channel_playlists_tab(data, channel_id)
        logger.info(
            'Playlists: %d playlists fetched for %s',
            len(result.playlists), channel_id,
        )
        return result

    async def aget_channel_playlists(self, channel_id: str) -> ChannelPlaylistsResult:
        """Async version of get_channel_playlists."""
        payload = InnerTube.build_playlists_tab_payload(channel_id)
        response = await self._http.apost(
            InnerTube.BROWSE_URL, json=payload,
            params={'prettyPrint': 'false'},
        )
        data = response.json()
        return ResponseParser.parse_channel_playlists_tab(data, channel_id)

    # ── Channel Search ──

    def search_channel(self, channel_id: str, query: str) -> SearchResult:
        """Search within a channel's videos.

        Args:
            channel_id: YouTube channel ID (UC...).
            query: Search query string.

        Returns:
            SearchResult containing matched videos.
        """
        payload = InnerTube.build_channel_search_payload(channel_id, query)
        response = self._http.post(
            InnerTube.BROWSE_URL, json=payload,
            params={'prettyPrint': 'false'},
        )
        data = response.json()
        result = ResponseParser.parse_channel_search(data, channel_id, query)
        logger.info(
            'Channel search %r: %d videos found in %s',
            query, len(result.videos), channel_id,
        )
        return result

    async def asearch_channel(self, channel_id: str, query: str) -> SearchResult:
        """Async version of search_channel."""
        payload = InnerTube.build_channel_search_payload(channel_id, query)
        response = await self._http.apost(
            InnerTube.BROWSE_URL, json=payload,
            params={'prettyPrint': 'false'},
        )
        data = response.json()
        return ResponseParser.parse_channel_search(data, channel_id, query)

    async def aget_channel_videos(
        self,
        channel_id: str,
        max_results: int = 30,
    ) -> BrowseResult:
        """Async version of get_channel_videos."""
        all_videos: list[VideoResult] = []

        payload = InnerTube.build_browse_payload(channel_id)
        response = await self._http.apost(
            InnerTube.BROWSE_URL,
            json=payload,
            params={'prettyPrint': 'false'},
        )
        data = response.json()

        channel_name = ResponseParser.extract_channel_name(data)
        videos, continuation = ResponseParser.parse_browse_first_page(data, channel_id)
        all_videos.extend(videos)
        page = 1

        while continuation:
            if max_results > 0 and len(all_videos) >= max_results:
                all_videos = all_videos[:max_results]
                break

            page += 1
            payload = InnerTube.build_browse_payload(channel_id, continuation=continuation)

            try:
                response = await self._http.apost(
                    InnerTube.BROWSE_URL,
                    json=payload,
                    params={'prettyPrint': 'false'},
                )
                data = response.json()
            except Exception as exc:
                logger.warning('[page %d] Browse continuation failed: %s', page, exc)
                break

            videos, continuation = ResponseParser.parse_browse_continuation(data)
            if not videos:
                break

            all_videos.extend(videos)

        if max_results > 0:
            all_videos = all_videos[:max_results]

        if channel_name or channel_id:
            all_videos = [
                dataclasses.replace(
                    v,
                    channel=v.channel or channel_name or '',
                    channel_id=v.channel_id or channel_id,
                ) if not v.channel or not v.channel_id else v
                for v in all_videos
            ]

        return BrowseResult(
            channel_id=channel_id, channel=channel_name, videos=all_videos,
        )
