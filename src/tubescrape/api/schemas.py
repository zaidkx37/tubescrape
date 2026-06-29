from __future__ import annotations

from pydantic import BaseModel


class ThumbnailResponse(BaseModel):
    url: str
    width: int
    height: int


class VideoResponse(BaseModel):
    video_id: str
    title: str
    channel: str
    channel_id: str | None
    duration: str | None
    duration_seconds: int
    published_text: str | None
    url: str
    is_live: bool
    is_short: bool
    view_count: str | None = None
    short_view_count: str | None = None
    thumbnails: list[ThumbnailResponse] = []
    moving_thumbnail: str | None = None
    channel_thumbnail: str | None = None
    description_snippet: str | None = None
    is_verified: bool = False
    badges: list[str] = []


class ChannelSearchResponse(BaseModel):
    channel_id: str
    title: str
    url: str
    description: str | None = None
    subscriber_count: str | None = None
    video_count: str | None = None
    thumbnails: list[ThumbnailResponse] = []


class SearchResponse(BaseModel):
    query: str
    videos: list[VideoResponse]
    channels: list[ChannelSearchResponse] = []


class BrowseResponse(BaseModel):
    channel_id: str
    channel: str | None = None
    videos: list[VideoResponse]


class TranscriptSegmentResponse(BaseModel):
    text: str
    start: float
    duration: float


class TranscriptResponse(BaseModel):
    video_id: str
    language: str
    language_code: str
    is_generated: bool
    segments: list[TranscriptSegmentResponse]
    translation_language: str | None
    text: str


class TranscriptLanguageResponse(BaseModel):
    language: str
    language_code: str
    is_generated: bool
    is_translatable: bool


class PlaylistVideoResponse(BaseModel):
    video_id: str
    title: str
    channel: str
    duration: str | None
    duration_seconds: int
    url: str
    thumbnails: list[ThumbnailResponse] = []


class PlaylistResponse(BaseModel):
    playlist_id: str
    title: str | None
    channel: str | None
    videos: list[PlaylistVideoResponse]
    url: str


class ShortResponse(BaseModel):
    video_id: str
    title: str
    url: str
    view_count: str | None = None
    thumbnail_url: str | None = None


class ShortsResponse(BaseModel):
    channel_id: str
    shorts: list[ShortResponse]


class ChannelPlaylistEntryResponse(BaseModel):
    playlist_id: str
    title: str
    url: str
    thumbnail_url: str | None = None
    video_count: str | None = None


class ChannelPlaylistsResponse(BaseModel):
    channel_id: str
    playlists: list[ChannelPlaylistEntryResponse]


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str = 'ok'
    version: str
