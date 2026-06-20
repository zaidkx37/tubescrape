"""tubescrape — YouTube scraping toolkit.

Search videos, browse channels, fetch transcripts, and scrape playlists.
No API key required.

Usage::

    from tubescrape import YouTube

    yt = YouTube()
    results = yt.search('python tutorial')
    transcript = yt.get_transcript('dQw4w9WgXcQ')
    playlist = yt.get_playlist('PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf')
"""

from tubescrape.client import YouTube
from tubescrape.exceptions import (
    AgeRestrictedError,
    APIKeyNotFoundError,
    BotDetectedError,
    ChannelNotFoundError,
    ParsingError,
    PlaylistNotFoundError,
    RateLimitError,
    RequestError,
    TranscriptFetchError,
    TranscriptsDisabledError,
    TranscriptsNotAvailableError,
    TranslationNotAvailableError,
    VideoUnavailableError,
    YouTubeError,
)
from tubescrape.models import (
    BrowseResult,
    ChannelPlaylistEntry,
    ChannelPlaylistsResult,
    PlaylistEntry,
    PlaylistResult,
    SearchResult,
    ShortResult,
    ShortsResult,
    Thumbnail,
    Transcript,
    TranscriptListEntry,
    TranscriptSegment,
    TranslationLanguage,
    VideoResult,
)

__version__ = '0.1.4'

__all__ = [
    # Client
    'YouTube',
    # Models
    'BrowseResult',
    'ChannelPlaylistEntry',
    'ChannelPlaylistsResult',
    'PlaylistEntry',
    'PlaylistResult',
    'SearchResult',
    'ShortResult',
    'ShortsResult',
    'Thumbnail',
    'Transcript',
    'TranslationLanguage',
    'TranscriptListEntry',
    'TranscriptSegment',
    'VideoResult',
    # Exceptions
    'AgeRestrictedError',
    'APIKeyNotFoundError',
    'BotDetectedError',
    'ChannelNotFoundError',
    'ParsingError',
    'PlaylistNotFoundError',
    'RateLimitError',
    'RequestError',
    'TranscriptFetchError',
    'TranscriptsDisabledError',
    'TranscriptsNotAvailableError',
    'TranslationNotAvailableError',
    'VideoUnavailableError',
    'YouTubeError',
    # Version
    '__version__',
]
