from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from tubescrape.api.deps import get_youtube
from tubescrape.api.schemas import (
    BrowseResponse,
    ChannelPlaylistsResponse,
    SearchResponse,
    ShortsResponse,
)
from tubescrape.client import YouTube

router = APIRouter()


@router.get('/channel/{channel_id}/videos', response_model=BrowseResponse)
async def channel_videos(
    channel_id: str,
    max_results: int = Query(30, ge=0, description='Maximum videos (0 for all)'),
    yt: YouTube = Depends(get_youtube),
) -> BrowseResponse:
    """Browse a YouTube channel's videos."""
    result = await yt.aget_channel_videos(channel_id, max_results=max_results)
    return BrowseResponse(
        channel_id=result.channel_id,
        channel=result.channel,
        videos=[v.to_dict() for v in result.videos],
    )


@router.get('/channel/{channel_id}/shorts', response_model=ShortsResponse)
async def channel_shorts(
    channel_id: str,
    yt: YouTube = Depends(get_youtube),
) -> ShortsResponse:
    """Browse a YouTube channel's Shorts."""
    result = await yt.aget_channel_shorts(channel_id)
    return ShortsResponse(
        channel_id=result.channel_id,
        shorts=[s.to_dict() for s in result.shorts],
    )


@router.get('/channel/{channel_id}/playlists', response_model=ChannelPlaylistsResponse)
async def channel_playlists(
    channel_id: str,
    yt: YouTube = Depends(get_youtube),
) -> ChannelPlaylistsResponse:
    """Browse a YouTube channel's playlists."""
    result = await yt.aget_channel_playlists(channel_id)
    return ChannelPlaylistsResponse(
        channel_id=result.channel_id,
        playlists=[p.to_dict() for p in result.playlists],
    )


@router.get('/channel/{channel_id}/search', response_model=SearchResponse)
async def channel_search(
    channel_id: str,
    q: str = Query(..., description='Search query'),
    yt: YouTube = Depends(get_youtube),
) -> SearchResponse:
    """Search within a YouTube channel's videos."""
    result = await yt.asearch_channel(channel_id, q)
    return SearchResponse(
        query=result.query,
        videos=[v.to_dict() for v in result.videos],
    )
