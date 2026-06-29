from __future__ import annotations

import logging

from tubescrape._filters import SearchFilter
from tubescrape._http import HTTPClient
from tubescrape._innertube import InnerTube
from tubescrape._parsers import ResponseParser
from tubescrape.models import SearchResult

logger = logging.getLogger('tubescrape.search')


class YouTubeSearch:
    """Search YouTube videos via the InnerTube search API.

    No API key required. Uses the same endpoint the YouTube web client uses.

    Args:
        http_client: HTTPClient instance for making requests.
    """

    def __init__(self, http_client: HTTPClient):
        self._http = http_client

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
        """Search YouTube and return video results.

        Args:
            query: Search query string.
            max_results: Maximum number of results to return. Use 0 for all
                         available results.
            params: Raw protobuf-encoded search filter (base64 string).
                    Ignored if any named filter is provided.
            sort_by: Sort order - 'relevance', 'upload_date', 'view_count', 'rating'.
            upload_date: Time filter - 'last_hour', 'today', 'this_week', 'this_month', 'this_year'.
            type: Content type - 'video', 'channel', 'playlist', 'movie'.
            duration: Duration filter - 'short' (<4min), 'medium' (4-20min), 'long' (>20min).
            features: Feature filter(s) - 'live', '4k', 'hd', 'subtitles', etc.

        Returns:
            SearchResult containing matched videos and/or channels.
        """
        filter_params = self._build_params(
            params, sort_by, upload_date, type, duration, features,
        )
        payload = InnerTube.build_search_payload(query, params=filter_params)

        logger.info('Searching: %r (max_results=%d)', query, max_results)
        response = self._http.post(
            InnerTube.SEARCH_URL,
            json=payload,
            params={'prettyPrint': 'false'},
        )
        data = response.json()

        result, continuation = ResponseParser.parse_search_response(
            data, query, max_results,
        )
        all_videos = list(result.videos)
        all_channels = list(result.channels)
        total = len(all_videos) + len(all_channels)
        page = 1
        logger.info(
            '[page %d] %d results fetched (total: %d)',
            page, total, total,
        )

        while continuation:
            if max_results > 0 and total >= max_results:
                break

            page += 1
            remaining = (max_results - total) if max_results > 0 else 0
            cont_payload = InnerTube.build_search_payload(
                query, params=filter_params, continuation=continuation,
            )

            try:
                response = self._http.post(
                    InnerTube.SEARCH_URL,
                    json=cont_payload,
                    params={'prettyPrint': 'false'},
                )
                data = response.json()
            except Exception as exc:
                logger.warning(
                    '[page %d] Search continuation failed: %s', page, exc,
                )
                break

            videos, channels, continuation = ResponseParser.parse_search_continuation(
                data, remaining,
            )
            if not videos and not channels:
                logger.info('[page %d] No more results, stopping', page)
                break

            all_videos.extend(videos)
            all_channels.extend(channels)
            total = len(all_videos) + len(all_channels)
            logger.info(
                '[page %d] %d results fetched (total: %d)',
                page, len(videos) + len(channels), total,
            )

        if max_results > 0:
            all_videos = all_videos[:max_results]
            all_channels = all_channels[:max_results]

        logger.info(
            'Search complete: %d pages, %d videos, %d channels',
            page, len(all_videos), len(all_channels),
        )
        return SearchResult(
            query=query, videos=all_videos, channels=all_channels,
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
        filter_params = self._build_params(
            params, sort_by, upload_date, type, duration, features,
        )
        payload = InnerTube.build_search_payload(query, params=filter_params)

        logger.info('Searching (async): %r (max_results=%d)', query, max_results)
        response = await self._http.apost(
            InnerTube.SEARCH_URL,
            json=payload,
            params={'prettyPrint': 'false'},
        )
        data = response.json()

        result, continuation = ResponseParser.parse_search_response(
            data, query, max_results,
        )
        all_videos = list(result.videos)
        all_channels = list(result.channels)
        total = len(all_videos) + len(all_channels)
        page = 1

        while continuation:
            if max_results > 0 and total >= max_results:
                break

            page += 1
            remaining = (max_results - total) if max_results > 0 else 0
            cont_payload = InnerTube.build_search_payload(
                query, params=filter_params, continuation=continuation,
            )

            try:
                response = await self._http.apost(
                    InnerTube.SEARCH_URL,
                    json=cont_payload,
                    params={'prettyPrint': 'false'},
                )
                data = response.json()
            except Exception as exc:
                logger.warning(
                    '[page %d] Search continuation failed: %s', page, exc,
                )
                break

            videos, channels, continuation = ResponseParser.parse_search_continuation(
                data, remaining,
            )
            if not videos and not channels:
                break

            all_videos.extend(videos)
            all_channels.extend(channels)
            total = len(all_videos) + len(all_channels)

        if max_results > 0:
            all_videos = all_videos[:max_results]
            all_channels = all_channels[:max_results]

        return SearchResult(
            query=query, videos=all_videos, channels=all_channels,
        )

    @staticmethod
    def _build_params(
        raw_params: str,
        sort_by: str | None,
        upload_date: str | None,
        type: str | None,
        duration: str | None,
        features: str | list[str] | None,
    ) -> str:
        """Build protobuf filter from named params, falling back to raw."""
        has_named = any([sort_by, upload_date, type, duration, features])
        if has_named:
            return SearchFilter.build(
                sort_by=sort_by,
                upload_date=upload_date,
                type=type,
                duration=duration,
                features=features,
            )
        return raw_params
