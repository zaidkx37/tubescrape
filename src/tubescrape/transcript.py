from __future__ import annotations

import logging
import re

from tubescrape._http import HTTPClient
from tubescrape._innertube import InnerTube
from tubescrape._parsers import ResponseParser
from tubescrape.exceptions import (
    AgeRestrictedError,
    BotDetectedError,
    CaptchaError,
    TranscriptFetchError,
    TranscriptsDisabledError,
    TranscriptsNotAvailableError,
    TranslationNotAvailableError,
)
from tubescrape.models import Transcript, TranscriptListEntry, TranscriptSegment, VideoInfo

logger = logging.getLogger('tubescrape.transcript')

# Global API key cache shared across all YouTubeTranscript instances.
_api_key_cache: str | None = None


class YouTubeTranscript:
    """Fetch YouTube transcripts via the InnerTube player API.

    No API key or third-party library needed. Uses the same endpoints
    the YouTube client uses.

    Args:
        http_client: HTTPClient instance for making requests.
    """

    MIN_TRANSCRIPT_LENGTH: int = 50

    def __init__(self, http_client: HTTPClient):
        self._http = http_client
        self._player_cache: dict = {}

    def list_transcripts(self, video_id: str) -> list[TranscriptListEntry]:
        """List available transcripts for a video.

        Args:
            video_id: YouTube video ID (e.g. 'dQw4w9WgXcQ').

        Returns:
            List of TranscriptListEntry with language and availability info.
            Each entry includes translation_languages if the track is translatable.
        """
        player_data = self._get_player_data(video_id)
        caption_tracks, translation_languages = ResponseParser.parse_player_captions(player_data)
        if not caption_tracks:
            raise TranscriptsDisabledError(video_id)
        return ResponseParser.parse_caption_tracks(caption_tracks, translation_languages)

    async def alist_transcripts(self, video_id: str) -> list[TranscriptListEntry]:
        """Async version of list_transcripts."""
        player_data = await self._aget_player_data(video_id)
        caption_tracks, translation_languages = ResponseParser.parse_player_captions(player_data)
        if not caption_tracks:
            raise TranscriptsDisabledError(video_id)
        return ResponseParser.parse_caption_tracks(caption_tracks, translation_languages)

    def get_video_info(self, video_id: str) -> VideoInfo | None:
        """Fetch video metadata from InnerTube player API.

        Uses the WEB client which returns richer metadata including exact
        publish/upload dates, category, and other microformat fields.
        Does not require residential proxies (uses main proxy pool).

        Args:
            video_id: YouTube video ID (e.g. 'dQw4w9WgXcQ').

        Returns:
            VideoInfo with title, channel, description, views, duration,
            publish_date, upload_date, category, etc.
            None if videoDetails is not available.
        """
        payload = InnerTube.build_player_web_payload(video_id)
        response = self._http.post(
            InnerTube.PLAYER_URL,
            json=payload,
            params={'prettyPrint': 'false'},
        )
        data = response.json()
        return ResponseParser.parse_video_details(data)

    async def aget_video_info(self, video_id: str) -> VideoInfo | None:
        """Async version of get_video_info."""
        payload = InnerTube.build_player_web_payload(video_id)
        response = await self._http.apost(
            InnerTube.PLAYER_URL,
            json=payload,
            params={'prettyPrint': 'false'},
        )
        data = response.json()
        return ResponseParser.parse_video_details(data)

    def get_transcript(
        self,
        video_id: str,
        languages: list[str] | None = None,
        timestamps: bool = True,
        translate_to: str | None = None,
    ) -> Transcript:
        """Fetch transcript for a video.

        Tries manually uploaded captions first, then auto-generated.

        Args:
            video_id: YouTube video ID.
            languages: Preferred language codes in priority order. Defaults to ['en'].
            timestamps: If True (default), return segments with timing info.
                        If False, return plain text without timestamps.
            translate_to: Target language code for translation (e.g. 'es', 'fr').
                          The transcript will be translated if the language is
                          available in YouTube's translation options.

        Returns:
            Transcript object with segments.

        Raises:
            TranslationNotAvailableError: If translate_to language is not available.
        """
        if languages is None:
            languages = ['en']

        player_data = self._get_player_data(video_id)
        caption_tracks, translation_languages = ResponseParser.parse_player_captions(player_data)
        if not caption_tracks:
            raise TranscriptsDisabledError(video_id)

        track_url, track_info = self._pick_track(
            caption_tracks, languages, translation_languages,
        )

        if not track_url:
            raise TranscriptsNotAvailableError(video_id)

        if translate_to:
            track_url, track_info = self._apply_translation(
                track_url, track_info, translate_to,
                translation_languages, video_id,
            )

        segments = self._fetch_transcript_segments(track_url)
        if not segments or self._is_transcript_empty(segments):
            raise TranscriptFetchError(video_id, reason='Transcript too short or empty')

        transcript = Transcript(
            video_id=video_id,
            language=track_info.get('language', ''),
            language_code=track_info.get('language_code', ''),
            is_generated=track_info.get('is_generated', False),
            segments=segments,
            translation_language=track_info.get('translation_language'),
        )

        if not timestamps:
            return transcript.without_timestamps()
        return transcript

    async def aget_transcript(
        self,
        video_id: str,
        languages: list[str] | None = None,
        timestamps: bool = True,
        translate_to: str | None = None,
    ) -> Transcript:
        """Async version of get_transcript."""
        if languages is None:
            languages = ['en']

        player_data = await self._aget_player_data(video_id)
        caption_tracks, translation_languages = ResponseParser.parse_player_captions(player_data)
        if not caption_tracks:
            raise TranscriptsDisabledError(video_id)

        track_url, track_info = self._pick_track(
            caption_tracks, languages, translation_languages,
        )

        if not track_url:
            raise TranscriptsNotAvailableError(video_id)

        if translate_to:
            track_url, track_info = self._apply_translation(
                track_url, track_info, translate_to,
                translation_languages, video_id,
            )

        segments = await self._afetch_transcript_segments(track_url)
        if not segments or self._is_transcript_empty(segments):
            raise TranscriptFetchError(video_id, reason='Transcript too short or empty')

        transcript = Transcript(
            video_id=video_id,
            language=track_info.get('language', ''),
            language_code=track_info.get('language_code', ''),
            is_generated=track_info.get('is_generated', False),
            segments=segments,
            translation_language=track_info.get('translation_language'),
        )

        if not timestamps:
            return transcript.without_timestamps()
        return transcript

    CAPTCHA_MAX_RETRIES: int = 3

    def _get_player_data(self, video_id: str) -> dict:
        """Fetch and cache InnerTube player response for a video.

        Uses the ANDROID client (returns caption tracks needed for transcripts).
        Tries without API key first. If that fails with empty captions,
        fetches the key from the watch page (cached globally) and retries.

        Retries with proxy rotation on captcha challenges.
        """
        if hasattr(self, '_player_cache') and self._player_cache.get('video_id') == video_id:
            return self._player_cache['data']

        last_error: Exception | None = None

        for attempt in range(self.CAPTCHA_MAX_RETRIES):
            url = self._build_player_url()
            payload = InnerTube.build_player_payload(video_id)
            response = self._http.transcript_post(
                url, json=payload, params={'prettyPrint': 'false'},
            )
            data = response.json()

            try:
                self._check_playability(data, video_id)
            except CaptchaError as exc:
                last_error = exc
                if attempt < self.CAPTCHA_MAX_RETRIES - 1:
                    logger.warning(
                        'Captcha for %s (attempt %d/%d), rotating proxy',
                        video_id, attempt + 1, self.CAPTCHA_MAX_RETRIES,
                    )
                    self._http._rotate_proxy()
                    continue
                raise

            # If captions are missing, the key-less request may have been
            # rejected silently. Fetch an API key and retry once.
            captions = data.get('captions')
            if captions is None or 'playerCaptionsTracklistRenderer' not in captions:
                refreshed = self._retry_with_api_key(video_id, data)
                if refreshed is not None:
                    data = refreshed

            self._player_cache = {'video_id': video_id, 'data': data}
            return data

        raise last_error or CaptchaError(video_id)

    async def _aget_player_data(self, video_id: str) -> dict:
        """Async version of _get_player_data with caching."""
        if hasattr(self, '_player_cache') and self._player_cache.get('video_id') == video_id:
            return self._player_cache['data']

        last_error: Exception | None = None

        for attempt in range(self.CAPTCHA_MAX_RETRIES):
            url = self._build_player_url()
            payload = InnerTube.build_player_payload(video_id)
            response = await self._http.transcript_apost(
                url, json=payload, params={'prettyPrint': 'false'},
            )
            data = response.json()

            try:
                self._check_playability(data, video_id)
            except CaptchaError as exc:
                last_error = exc
                if attempt < self.CAPTCHA_MAX_RETRIES - 1:
                    logger.warning(
                        'Captcha for %s (attempt %d/%d), rotating proxy',
                        video_id, attempt + 1, self.CAPTCHA_MAX_RETRIES,
                    )
                    self._http._rotate_proxy()
                    continue
                raise

            captions = data.get('captions')
            if captions is None or 'playerCaptionsTracklistRenderer' not in captions:
                refreshed = await self._aretry_with_api_key(video_id, data)
                if refreshed is not None:
                    data = refreshed

            self._player_cache = {'video_id': video_id, 'data': data}
            return data

        raise last_error or CaptchaError(video_id)

    def _retry_with_api_key(self, video_id: str, original_data: dict) -> dict | None:
        """Retry the player request with an API key if captions were missing."""
        api_key = self._ensure_api_key(video_id)
        if not api_key:
            return None

        logger.info('Retrying player request with API key for %s', video_id)
        payload = InnerTube.build_player_payload(video_id)
        url = f'{InnerTube.PLAYER_URL}?key={api_key}'
        response = self._http.transcript_post(
            url, json=payload, params={'prettyPrint': 'false'},
        )
        data = response.json()
        captions = data.get('captions')
        if captions and 'playerCaptionsTracklistRenderer' in captions:
            return data

        # Key may be stale, refresh it once
        logger.info('Cached API key may be stale, refreshing')
        api_key = self._fetch_api_key(video_id)
        if not api_key:
            return None

        url = f'{InnerTube.PLAYER_URL}?key={api_key}'
        response = self._http.transcript_post(
            url, json=payload, params={'prettyPrint': 'false'},
        )
        data = response.json()
        captions = data.get('captions')
        if captions and 'playerCaptionsTracklistRenderer' in captions:
            return data

        return None

    async def _aretry_with_api_key(self, video_id: str, original_data: dict) -> dict | None:
        """Async version of _retry_with_api_key."""
        api_key = await self._aensure_api_key(video_id)
        if not api_key:
            return None

        logger.info('Retrying player request with API key for %s', video_id)
        payload = InnerTube.build_player_payload(video_id)
        url = f'{InnerTube.PLAYER_URL}?key={api_key}'
        response = await self._http.transcript_apost(
            url, json=payload, params={'prettyPrint': 'false'},
        )
        data = response.json()
        captions = data.get('captions')
        if captions and 'playerCaptionsTracklistRenderer' in captions:
            return data

        logger.info('Cached API key may be stale, refreshing')
        api_key = await self._afetch_api_key(video_id)
        if not api_key:
            return None

        url = f'{InnerTube.PLAYER_URL}?key={api_key}'
        response = await self._http.transcript_apost(
            url, json=payload, params={'prettyPrint': 'false'},
        )
        data = response.json()
        captions = data.get('captions')
        if captions and 'playerCaptionsTracklistRenderer' in captions:
            return data

        return None

    @staticmethod
    def _build_player_url() -> str:
        """Build player URL, using cached API key if available."""
        global _api_key_cache
        if _api_key_cache:
            return f'{InnerTube.PLAYER_URL}?key={_api_key_cache}'
        return InnerTube.PLAYER_URL

    def _ensure_api_key(self, video_id: str) -> str | None:
        """Return cached API key, or fetch one from the watch page."""
        global _api_key_cache
        if _api_key_cache:
            return _api_key_cache
        return self._fetch_api_key(video_id)

    async def _aensure_api_key(self, video_id: str) -> str | None:
        """Async version of _ensure_api_key."""
        global _api_key_cache
        if _api_key_cache:
            return _api_key_cache
        return await self._afetch_api_key(video_id)

    def _fetch_api_key(self, video_id: str) -> str | None:
        """Fetch INNERTUBE_API_KEY from watch page and cache it globally."""
        global _api_key_cache
        try:
            response = self._http.transcript_get(
                InnerTube.WATCH_URL, params={'v': video_id},
            )
            key = self._extract_api_key(response.text)
            if key:
                _api_key_cache = key
                logger.info('Cached INNERTUBE_API_KEY: %s...', key[:10])
            return key
        except Exception as exc:
            logger.warning('Failed to fetch API key: %s', exc)
            return None

    async def _afetch_api_key(self, video_id: str) -> str | None:
        """Async version of _fetch_api_key."""
        global _api_key_cache
        try:
            response = await self._http.transcript_aget(
                InnerTube.WATCH_URL, params={'v': video_id},
            )
            key = self._extract_api_key(response.text)
            if key:
                _api_key_cache = key
                logger.info('Cached INNERTUBE_API_KEY: %s...', key[:10])
            return key
        except Exception as exc:
            logger.warning('Failed to fetch API key: %s', exc)
            return None

    @staticmethod
    def _extract_api_key(html: str) -> str | None:
        """Extract INNERTUBE_API_KEY from HTML page content."""
        match = re.search(r'"INNERTUBE_API_KEY":\s*"([a-zA-Z0-9_-]+)"', html)
        return match.group(1) if match else None

    @staticmethod
    def _check_playability(data: dict, video_id: str) -> None:
        """Check player response for errors (age restriction, captcha, bot detection)."""
        status = ResponseParser.extract_playability_status(data)
        status_value = status.get('status', '')
        reason = status.get('reason', '')

        if status_value in ('LOGIN_REQUIRED', 'ERROR'):
            if (
                status.get('desktopLegacyAgeGateReason')
                or 'inappropriate' in reason.lower()
            ):
                raise AgeRestrictedError(video_id, reason)

            if 'not a bot' in reason.lower():
                raise CaptchaError(video_id)

            if 'bot' in reason.lower():
                raise BotDetectedError(video_id)

    @staticmethod
    def _pick_track(
        tracks: list[dict],
        languages: list[str],
        translation_languages: list[dict] | None = None,
    ) -> tuple[str | None, dict]:
        """Pick the best caption track URL for the requested languages.

        Priority:
            1. Manual track in requested language
            2. Auto-generated (ASR) track in requested language
            3. Any English variant (manual then auto)
            4. Translatable track -> translate via &tlang=
            5. First available track as fallback

        Returns:
            (track_url, track_info_dict) where track_info contains metadata
            about the selected track.
        """
        manual: dict[str, dict] = {}
        generated: dict[str, dict] = {}
        translatable: list[dict] = []

        for track in tracks:
            lang = track['languageCode']
            is_auto = track.get('kind', '') == 'asr'

            entry = {
                'url': track['baseUrl'],
                'language_code': lang,
                'language': ResponseParser.get_text(track.get('name', {}))
                    if isinstance(track.get('name'), dict) else str(track.get('name', '')),
                'is_generated': is_auto,
            }

            if is_auto:
                generated[lang] = entry
            else:
                manual[lang] = entry

            if track.get('isTranslatable', False):
                translatable.append(entry)

        # 1-2. Exact match: manual first, then auto-generated
        for lang in languages:
            if lang in manual:
                info = manual[lang]
                logger.info('Found manual %s transcript', lang)
                return info['url'], info

            if lang in generated:
                info = generated[lang]
                logger.info('Found auto-generated %s transcript', lang)
                return info['url'], info

        # 3. Any English variant
        for lang_code in list(manual.keys()) + list(generated.keys()):
            if lang_code.startswith('en'):
                info = manual.get(lang_code) or generated.get(lang_code, {})
                if info:
                    logger.info(
                        'No exact %s match, using English variant: %s',
                        languages, lang_code,
                    )
                    return info['url'], info

        # 4. Translate a non-English track to the requested language
        if translatable and translation_languages:
            available_langs = {tl['languageCode'] for tl in translation_languages}
            for lang in languages:
                if lang in available_langs:
                    source = translatable[0]
                    url = '{}&tlang={}'.format(source['url'], lang)
                    info = {**source, 'translation_language': lang}
                    logger.info(
                        'Translating %s transcript to %s',
                        source['language_code'], lang,
                    )
                    return url, info

        # 5. Return whatever is available
        if tracks:
            first = manual.get(tracks[0]['languageCode']) or generated.get(
                tracks[0]['languageCode']
            )
            if first:
                logger.warning(
                    'Falling back to original language: %s',
                    first['language_code'],
                )
                return first['url'], first

        return None, {}

    @staticmethod
    def _apply_translation(
        track_url: str,
        track_info: dict,
        translate_to: str,
        translation_languages: list[dict] | None,
        video_id: str,
    ) -> tuple[str, dict]:
        """Apply translation to a track URL if the target language is available.

        Args:
            track_url: Base caption track URL.
            track_info: Track metadata dict.
            translate_to: Target language code (e.g. 'es').
            translation_languages: List of available translation language dicts.
            video_id: Video ID for error messages.

        Returns:
            (translated_url, updated_track_info)

        Raises:
            TranslationNotAvailableError: If the language is not available.
        """
        if not translation_languages:
            raise TranslationNotAvailableError(video_id, translate_to)

        available = {tl['languageCode'] for tl in translation_languages}
        if translate_to not in available:
            raise TranslationNotAvailableError(video_id, translate_to)

        url = f'{track_url}&tlang={translate_to}'
        info = {**track_info, 'translation_language': translate_to}
        logger.info(
            'Translating %s transcript to %s',
            track_info.get('language_code', '?'), translate_to,
        )
        return url, info

    def _fetch_transcript_segments(self, url: str) -> list[TranscriptSegment]:
        """Fetch and parse transcript XML from a caption track URL."""
        response = self._http.transcript_get(url)
        return ResponseParser.parse_transcript_xml(response.text)

    async def _afetch_transcript_segments(self, url: str) -> list[TranscriptSegment]:
        """Async version of _fetch_transcript_segments."""
        response = await self._http.transcript_aget(url)
        return ResponseParser.parse_transcript_xml(response.text)

    @staticmethod
    def _is_transcript_empty(segments: list[TranscriptSegment]) -> bool:
        """Check if the transcript is too short to be useful."""
        total_text = ' '.join(s.text for s in segments)
        return len(total_text.strip()) < YouTubeTranscript.MIN_TRANSCRIPT_LENGTH
