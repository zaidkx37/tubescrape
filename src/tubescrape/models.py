from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Thumbnail:
    """A single thumbnail image with URL and dimensions."""

    url: str
    width: int
    height: int

    def to_dict(self) -> dict:
        return {
            'url': self.url,
            'width': self.width,
            'height': self.height,
        }


@dataclass(frozen=True, slots=True)
class VideoResult:
    """A single YouTube video from search or channel browse results."""

    video_id: str
    title: str
    channel: str
    channel_id: str | None
    duration: str | None
    duration_seconds: int
    published_text: str | None
    url: str
    is_live: bool = False
    is_short: bool = False
    view_count: str | None = None
    short_view_count: str | None = None
    thumbnails: list[Thumbnail] = field(default_factory=list)
    moving_thumbnail: str | None = None
    channel_thumbnail: str | None = None
    description_snippet: str | None = None
    is_verified: bool = False
    badges: list[str] = field(default_factory=list)

    @property
    def channel_url(self) -> str | None:
        if self.channel_id:
            return f'https://www.youtube.com/channel/{self.channel_id}'
        return None

    @property
    def thumbnail_url(self) -> str | None:
        """Return the highest-resolution thumbnail URL, or None."""
        if self.thumbnails:
            return self.thumbnails[-1].url
        return None

    def to_dict(self) -> dict:
        result: dict = {
            'video_id': self.video_id,
            'title': self.title,
            'channel': self.channel,
            'channel_id': self.channel_id,
            'duration': self.duration,
            'duration_seconds': self.duration_seconds,
            'published_text': self.published_text,
            'url': self.url,
            'is_live': self.is_live,
            'is_short': self.is_short,
        }
        if self.view_count is not None:
            result['view_count'] = self.view_count
        if self.short_view_count is not None:
            result['short_view_count'] = self.short_view_count
        if self.thumbnails:
            result['thumbnails'] = [t.to_dict() for t in self.thumbnails]
        if self.moving_thumbnail is not None:
            result['moving_thumbnail'] = self.moving_thumbnail
        if self.channel_thumbnail is not None:
            result['channel_thumbnail'] = self.channel_thumbnail
        if self.description_snippet is not None:
            result['description_snippet'] = self.description_snippet
        if self.is_verified:
            result['is_verified'] = self.is_verified
        if self.badges:
            result['badges'] = self.badges
        return result


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    """A single segment of a transcript with timing information."""

    text: str
    start: float
    duration: float

    def to_dict(self) -> dict:
        return {
            'text': self.text,
            'start': self.start,
            'duration': self.duration,
        }


@dataclass(frozen=True, slots=True)
class Transcript:
    """A fetched transcript with all segments."""

    video_id: str
    language: str
    language_code: str
    is_generated: bool
    segments: list[TranscriptSegment] = field(default_factory=list)
    translation_language: str | None = None

    @property
    def text(self) -> str:
        """Join all segments into a single string."""
        return ' '.join(s.text for s in self.segments)

    def to_dict(self, timestamps: bool = True) -> dict:
        result = {
            'video_id': self.video_id,
            'language': self.language,
            'language_code': self.language_code,
            'is_generated': self.is_generated,
            'translation_language': self.translation_language,
            'text': self.text,
        }
        if timestamps:
            result['segments'] = [s.to_dict() for s in self.segments]
        return result

    def without_timestamps(self) -> Transcript:
        """Return a copy with segments stripped of timing info.

        Collapses all segments into a single segment with the full text
        and zeroed timing. Useful when only the raw text is needed.
        """
        return Transcript(
            video_id=self.video_id,
            language=self.language,
            language_code=self.language_code,
            is_generated=self.is_generated,
            segments=[TranscriptSegment(text=self.text, start=0.0, duration=0.0)],
            translation_language=self.translation_language,
        )

    def save(
        self,
        filename: str,
        format: str | None = None,
        encoding: str = 'utf-8',
    ) -> Path:
        """Save the transcript to a file.

        The format is inferred from the file extension unless explicitly set.

        Args:
            filename: Output file path (e.g. 'transcript.srt', 'output.json').
                      Extension is added automatically if missing and format is given.
            format: Output format — 'text', 'txt', 'json', 'srt', 'vtt', 'webvtt'.
                    If None, inferred from filename extension.
            encoding: File encoding. Defaults to 'utf-8'.

        Returns:
            Path object pointing to the saved file.

        Raises:
            ValueError: If format cannot be determined.

        Examples::

            transcript.save('subtitles.srt')
            transcript.save('output.json')
            transcript.save('transcript.vtt')
            transcript.save('plain', format='text')
            transcript.save('transcript', format='srt')
        """
        from tubescrape.formatters import FORMATTERS, get_formatter

        path = Path(filename)

        # Determine format
        if format is None:
            ext = path.suffix.lstrip('.')
            if ext in FORMATTERS:
                format = ext
            else:
                raise ValueError(
                    f'Cannot determine format from filename {filename!r}. '
                    'Either use a recognized extension (.srt, .vtt, .json, .txt) '
                    'or pass format= explicitly.'
                )
        else:
            format = format.lower()

        # Add extension if missing
        if not path.suffix:
            ext_map = {
                'text': '.txt', 'txt': '.txt', 'json': '.json',
                'srt': '.srt', 'vtt': '.vtt', 'webvtt': '.vtt',
            }
            ext = ext_map.get(format, '.txt')
            path = path.with_suffix(ext)

        formatter = get_formatter(format)
        content = formatter.format(self)

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding=encoding)
        return path


@dataclass(frozen=True, slots=True)
class TranslationLanguage:
    """A language available for transcript translation."""

    language: str
    language_code: str

    def to_dict(self) -> dict:
        return {
            'language': self.language,
            'language_code': self.language_code,
        }


@dataclass(frozen=True, slots=True)
class TranscriptListEntry:
    """Metadata about an available transcript (before fetching)."""

    language: str
    language_code: str
    is_generated: bool
    is_translatable: bool
    base_url: str = field(repr=False)
    translation_languages: tuple[TranslationLanguage, ...] = field(default=(), repr=False)

    def to_dict(self) -> dict:
        return {
            'language': self.language,
            'language_code': self.language_code,
            'is_generated': self.is_generated,
            'is_translatable': self.is_translatable,
            'translation_languages': [tl.to_dict() for tl in self.translation_languages],
        }


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Results from a YouTube search query."""

    query: str
    videos: list[VideoResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'query': self.query,
            'videos': [v.to_dict() for v in self.videos],
        }


@dataclass(frozen=True, slots=True)
class BrowseResult:
    """Results from browsing a YouTube channel's videos."""

    channel_id: str
    videos: list[VideoResult] = field(default_factory=list)
    continuation_token: str | None = None

    def to_dict(self) -> dict:
        return {
            'channel_id': self.channel_id,
            'videos': [v.to_dict() for v in self.videos],
        }


@dataclass(frozen=True, slots=True)
class ShortResult:
    """A YouTube Short from a channel's Shorts tab."""

    video_id: str
    title: str
    view_count: str | None = None
    thumbnail_url: str | None = None

    @property
    def url(self) -> str:
        return f'https://www.youtube.com/shorts/{self.video_id}'

    def to_dict(self) -> dict:
        result: dict = {
            'video_id': self.video_id,
            'title': self.title,
            'url': self.url,
        }
        if self.view_count is not None:
            result['view_count'] = self.view_count
        if self.thumbnail_url is not None:
            result['thumbnail_url'] = self.thumbnail_url
        return result


@dataclass(frozen=True, slots=True)
class ShortsResult:
    """Results from browsing a channel's Shorts tab."""

    channel_id: str
    shorts: list[ShortResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'channel_id': self.channel_id,
            'shorts': [s.to_dict() for s in self.shorts],
        }


@dataclass(frozen=True, slots=True)
class ChannelPlaylistEntry:
    """A playlist from a channel's Playlists tab."""

    playlist_id: str
    title: str
    thumbnail_url: str | None = None
    video_count: str | None = None

    @property
    def url(self) -> str:
        return f'https://www.youtube.com/playlist?list={self.playlist_id}'

    def to_dict(self) -> dict:
        result: dict = {
            'playlist_id': self.playlist_id,
            'title': self.title,
            'url': self.url,
        }
        if self.thumbnail_url is not None:
            result['thumbnail_url'] = self.thumbnail_url
        if self.video_count is not None:
            result['video_count'] = self.video_count
        return result


@dataclass(frozen=True, slots=True)
class ChannelPlaylistsResult:
    """Results from browsing a channel's Playlists tab."""

    channel_id: str
    playlists: list[ChannelPlaylistEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'channel_id': self.channel_id,
            'playlists': [p.to_dict() for p in self.playlists],
        }


@dataclass(frozen=True, slots=True)
class PlaylistEntry:
    """A single video within a playlist."""

    video_id: str
    title: str
    channel: str
    duration: str | None
    duration_seconds: int
    position: int
    url: str
    thumbnails: list[Thumbnail] = field(default_factory=list)

    @property
    def thumbnail_url(self) -> str | None:
        """Return the highest-resolution thumbnail URL, or None."""
        if self.thumbnails:
            return self.thumbnails[-1].url
        return None

    def to_dict(self) -> dict:
        result: dict = {
            'video_id': self.video_id,
            'title': self.title,
            'channel': self.channel,
            'duration': self.duration,
            'duration_seconds': self.duration_seconds,
            'position': self.position,
            'url': self.url,
        }
        if self.thumbnails:
            result['thumbnails'] = [t.to_dict() for t in self.thumbnails]
        return result


@dataclass(frozen=True, slots=True)
class PlaylistResult:
    """Results from fetching a YouTube playlist."""

    playlist_id: str
    title: str | None = None
    channel: str | None = None
    videos: list[PlaylistEntry] = field(default_factory=list)

    @property
    def url(self) -> str:
        return f'https://www.youtube.com/playlist?list={self.playlist_id}'

    def to_dict(self) -> dict:
        return {
            'playlist_id': self.playlist_id,
            'title': self.title,
            'channel': self.channel,
            'videos': [v.to_dict() for v in self.videos],
            'url': self.url,
        }
