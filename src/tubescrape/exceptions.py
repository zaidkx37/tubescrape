from __future__ import annotations


class YouTubeError(Exception):
    """Base exception for all tubescrape errors."""

    def __init__(self, message: str, video_id: str | None = None):
        self.video_id = video_id
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}: {self.message}'


class RequestError(YouTubeError):
    """HTTP request failed after retries."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


class RateLimitError(RequestError):
    """Request was rate-limited by YouTube (HTTP 429)."""

    def __init__(self, message: str = 'Rate limited by YouTube (429)'):
        super().__init__(message, status_code=429)


class VideoUnavailableError(YouTubeError):
    """Video is unavailable (deleted, private, region-locked)."""

    def __init__(self, video_id: str, reason: str | None = None):
        self.reason = reason or 'Video unavailable'
        super().__init__(
            f'Video unavailable: {video_id} ({self.reason})',
            video_id=video_id,
        )


class AgeRestrictedError(VideoUnavailableError):
    """Video requires age verification."""

    def __init__(self, video_id: str, reason: str | None = None):
        super().__init__(video_id, reason=reason or 'Age-restricted content')


class TranscriptsDisabledError(YouTubeError):
    """Transcripts are disabled for this video."""

    def __init__(self, video_id: str):
        super().__init__(
            f'Transcripts are disabled for {video_id}',
            video_id=video_id,
        )


class TranscriptsNotAvailableError(YouTubeError):
    """No transcripts available in the requested language."""

    def __init__(self, video_id: str):
        super().__init__(
            f'Transcripts not available for {video_id}',
            video_id=video_id,
        )


class TranscriptFetchError(YouTubeError):
    """Failed to fetch or parse the transcript content."""

    def __init__(self, video_id: str, reason: str | None = None):
        self.reason = reason or 'Fetch failed'
        super().__init__(
            f'Transcript fetch failed for {video_id}: {self.reason}',
            video_id=video_id,
        )


class TranslationNotAvailableError(YouTubeError):
    """Requested translation language is not available for this video."""

    def __init__(self, video_id: str, language: str):
        self.language = language
        super().__init__(
            f'Translation to {language!r} is not available for {video_id}',
            video_id=video_id,
        )


class PlaylistNotFoundError(YouTubeError):
    """Playlist could not be found or is empty."""

    def __init__(self, playlist_id: str):
        self.playlist_id = playlist_id
        super().__init__(f'Playlist not found: {playlist_id}')


class ChannelNotFoundError(YouTubeError):
    """Channel ID or handle could not be resolved."""

    def __init__(self, channel: str):
        self.channel = channel
        super().__init__(f'Channel not found: {channel}')


class APIKeyNotFoundError(YouTubeError):
    """INNERTUBE_API_KEY could not be extracted from the watch page."""

    def __init__(self, video_id: str):
        super().__init__(
            f'INNERTUBE_API_KEY not found for {video_id}',
            video_id=video_id,
        )


class ParsingError(YouTubeError):
    """Failed to parse YouTube response (structure may have changed)."""

    def __init__(self, message: str = 'Failed to parse YouTube response'):
        super().__init__(message)


class ProxyBlockedError(RequestError):
    """Proxy was blocked by a firewall or content filter (datacenter IP rejected)."""

    # Signatures found in 403 response bodies from corporate firewalls
    FIREWALL_SIGNATURES: tuple[str, ...] = (
        'Web Filter Violation',
        'FortiGate Application Control',
        'Application Blocked',
        'Web Page Blocked',
        'Blocked',
        'Banned',
    )

    def __init__(self, message: str = 'Proxy blocked by firewall'):
        super().__init__(message, status_code=403)


class CaptchaError(RequestError):
    """YouTube triggered a captcha / bot verification challenge."""

    def __init__(self, video_id: str | None = None):
        super().__init__(
            'Captcha triggered%s' % (
                f' for {video_id}' if video_id else ''
            ),
            status_code=429,
        )
        self.video_id = video_id


class BotDetectedError(RequestError):
    """YouTube detected automated access."""

    def __init__(self, video_id: str | None = None):
        super().__init__(
            'Bot detection triggered%s' % (
                f' for {video_id}' if video_id else ''
            ),
            status_code=403,
        )
