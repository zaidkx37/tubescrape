"""Live end-to-end tests against the real YouTube API.

These tests hit the actual YouTube InnerTube API.  They verify the full
pipeline — HTTP transport → response parsing → model construction — with
real video IDs, channel IDs, handles, and playlist IDs.

Run with:
    pytest tests/test_live.py -v --timeout=60

Skip in CI or offline environments:
    pytest tests/test_live.py -v -k "not live"

Well-known test fixtures
========================
- Channel: Lex Fridman  @lexfridman  UCJIfeSCssxSC_Dhc5s7woww
- Video:   Lex Fridman #400 (Elon Musk)  JN3KPFbWCy8
- Playlist: Lex Fridman Podcast clips  PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf
- Rick Astley video (for transcripts): dQw4w9WgXcQ
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get('CI') == 'true',
    reason='Live tests skipped in CI (requires real YouTube API access)',
)

from tubescrape import (
    YouTube,
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
    VideoResult,
)
from tubescrape.exceptions import (
    ChannelNotFoundError,
    PlaylistNotFoundError,
    TranscriptsDisabledError,
    TranscriptsNotAvailableError,
    TranslationNotAvailableError,
    VideoUnavailableError,
    YouTubeError,
)

# ────────────────────────────────────────────────────────────────
# Constants
# ────────────────────────────────────────────────────────────────

LEX_CHANNEL_ID = 'UCJIfeSCssxSC_Dhc5s7woww'
LEX_HANDLE = '@lexfridman'
LEX_VIDEO_ID = 'JN3KPFbWCy8'          # Lex Fridman #400 (Elon Musk)
RICK_VIDEO_ID = 'dQw4w9WgXcQ'          # Rick Astley - Never Gonna Give You Up
LEX_PLAYLIST_ID = 'PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf'

# ────────────────────────────────────────────────────────────────
# Fixture: shared YouTube client
# ────────────────────────────────────────────────────────────────


@pytest.fixture(scope='module')
def yt() -> YouTube:
    """Shared YouTube client for the entire test module."""
    client = YouTube(timeout=30.0)
    yield client
    client.close()


# ════════════════════════════════════════════════════════════════
# 1.  SEARCH
# ════════════════════════════════════════════════════════════════


class TestSearch:
    """Search YouTube videos — basic, filtered, combined."""

    def test_basic_search(self, yt: YouTube):
        result = yt.search('python programming', max_results=5)

        assert isinstance(result, SearchResult)
        assert result.query == 'python programming'
        assert 1 <= len(result.videos) <= 5

    def test_search_video_fields(self, yt: YouTube):
        """Every video returned must have the core fields populated."""
        result = yt.search('machine learning tutorial', max_results=3)

        for video in result.videos:
            assert isinstance(video, VideoResult)
            assert len(video.video_id) == 11
            assert video.title
            assert video.channel
            assert video.url == f'https://www.youtube.com/watch?v={video.video_id}'
            assert video.duration_seconds >= 0

    def test_search_rich_metadata(self, yt: YouTube):
        """Search results should include thumbnails and view counts."""
        result = yt.search('popular music video', max_results=5)

        with_thumbnails = [v for v in result.videos if v.thumbnails]
        assert len(with_thumbnails) >= 1, 'At least one video should have thumbnails'

        for video in with_thumbnails:
            thumb = video.thumbnails[0]
            assert isinstance(thumb, Thumbnail)
            assert thumb.url.startswith('https://')
            assert thumb.width > 0
            assert thumb.height > 0

        # thumbnail_url property
        assert with_thumbnails[0].thumbnail_url is not None

        with_views = [v for v in result.videos if v.view_count]
        assert len(with_views) >= 1, 'At least one video should have view counts'

    def test_search_filter_type_video(self, yt: YouTube):
        result = yt.search('python', type='video', max_results=5)
        assert len(result.videos) >= 1
        # type=video filter should only return videos (not channels/playlists)

    def test_search_filter_duration_long(self, yt: YouTube):
        result = yt.search('documentary', duration='long', max_results=5)
        assert len(result.videos) >= 1
        for video in result.videos:
            # "long" = > 20 min = > 1200 seconds
            if video.duration_seconds > 0:
                assert video.duration_seconds > 1200, (
                    f'{video.title}: {video.duration_seconds}s is not > 20 min'
                )

    def test_search_filter_upload_date(self, yt: YouTube):
        result = yt.search('news', upload_date='this_week', max_results=5)
        assert len(result.videos) >= 1

    def test_search_filter_sort_by_view_count(self, yt: YouTube):
        result = yt.search('python tutorial', sort_by='view_count', max_results=5)
        assert len(result.videos) >= 1

    def test_search_filter_features(self, yt: YouTube):
        result = yt.search('nature 4k', features='4k', max_results=3)
        assert len(result.videos) >= 1

    def test_search_combined_filters(self, yt: YouTube):
        result = yt.search(
            'podcast',
            type='video',
            duration='long',
            upload_date='this_month',
            sort_by='view_count',
            max_results=5,
        )
        assert isinstance(result, SearchResult)
        assert len(result.videos) >= 1

    def test_search_max_results_respected(self, yt: YouTube):
        result = yt.search('music', max_results=2)
        assert len(result.videos) <= 2

    def test_search_to_dict(self, yt: YouTube):
        result = yt.search('test', max_results=2)
        d = result.to_dict()

        assert d['query'] == 'test'
        assert isinstance(d['videos'], list)
        if d['videos']:
            v = d['videos'][0]
            assert 'video_id' in v
            assert 'title' in v
            assert 'url' in v

    def test_search_json_serializable(self, yt: YouTube):
        result = yt.search('hello', max_results=2)
        # Must not raise
        json_str = json.dumps(result.to_dict(), ensure_ascii=False)
        assert len(json_str) > 10


# ════════════════════════════════════════════════════════════════
# 2.  CHANNEL VIDEOS
# ════════════════════════════════════════════════════════════════


class TestChannelVideos:
    """Browse a channel's Videos tab."""

    def test_by_channel_id(self, yt: YouTube):
        result = yt.get_channel_videos(LEX_CHANNEL_ID, max_results=5)

        assert isinstance(result, BrowseResult)
        assert result.channel_id == LEX_CHANNEL_ID
        assert 1 <= len(result.videos) <= 5

    def test_by_handle(self, yt: YouTube):
        result = yt.get_channel_videos(LEX_HANDLE, max_results=3)

        assert isinstance(result, BrowseResult)
        assert result.channel_id == LEX_CHANNEL_ID
        assert len(result.videos) >= 1

    def test_by_full_url(self, yt: YouTube):
        result = yt.get_channel_videos(
            f'https://www.youtube.com/channel/{LEX_CHANNEL_ID}',
            max_results=3,
        )
        assert result.channel_id == LEX_CHANNEL_ID
        assert len(result.videos) >= 1

    def test_by_handle_url(self, yt: YouTube):
        result = yt.get_channel_videos(
            f'https://www.youtube.com/{LEX_HANDLE}',
            max_results=3,
        )
        assert result.channel_id == LEX_CHANNEL_ID
        assert len(result.videos) >= 1

    def test_channel_video_fields(self, yt: YouTube):
        result = yt.get_channel_videos(LEX_CHANNEL_ID, max_results=3)

        for video in result.videos:
            assert len(video.video_id) == 11
            assert video.title
            assert video.url.startswith('https://www.youtube.com/watch?v=')
            assert video.duration_seconds >= 0

    def test_channel_videos_have_thumbnails(self, yt: YouTube):
        result = yt.get_channel_videos(LEX_CHANNEL_ID, max_results=5)

        with_thumbs = [v for v in result.videos if v.thumbnails]
        assert len(with_thumbs) >= 1

    def test_channel_videos_max_results(self, yt: YouTube):
        result = yt.get_channel_videos(LEX_CHANNEL_ID, max_results=2)
        assert len(result.videos) <= 2

    def test_channel_videos_to_dict(self, yt: YouTube):
        result = yt.get_channel_videos(LEX_CHANNEL_ID, max_results=2)
        d = result.to_dict()
        assert d['channel_id'] == LEX_CHANNEL_ID
        assert isinstance(d['videos'], list)

    def test_channel_not_found(self, yt: YouTube):
        with pytest.raises((ChannelNotFoundError, YouTubeError)):
            yt.get_channel_videos('@this_channel_definitely_does_not_exist_xyz_12345')


# ════════════════════════════════════════════════════════════════
# 3.  CHANNEL SHORTS
# ════════════════════════════════════════════════════════════════


class TestChannelShorts:
    """Browse a channel's Shorts tab."""

    def test_get_shorts_by_id(self, yt: YouTube):
        result = yt.get_channel_shorts(LEX_CHANNEL_ID)

        assert isinstance(result, ShortsResult)
        assert result.channel_id == LEX_CHANNEL_ID
        assert len(result.shorts) >= 1

    def test_get_shorts_by_handle(self, yt: YouTube):
        result = yt.get_channel_shorts(LEX_HANDLE)

        assert isinstance(result, ShortsResult)
        assert result.channel_id == LEX_CHANNEL_ID
        assert len(result.shorts) >= 1

    def test_short_fields(self, yt: YouTube):
        result = yt.get_channel_shorts(LEX_CHANNEL_ID)

        for short in result.shorts:
            assert isinstance(short, ShortResult)
            assert len(short.video_id) == 11
            assert short.title
            assert short.url == f'https://www.youtube.com/shorts/{short.video_id}'

    def test_shorts_have_view_counts(self, yt: YouTube):
        result = yt.get_channel_shorts(LEX_CHANNEL_ID)
        with_views = [s for s in result.shorts if s.view_count]
        assert len(with_views) >= 1

    def test_shorts_have_thumbnails(self, yt: YouTube):
        result = yt.get_channel_shorts(LEX_CHANNEL_ID)
        with_thumbs = [s for s in result.shorts if s.thumbnail_url]
        assert len(with_thumbs) >= 1
        for s in with_thumbs:
            assert s.thumbnail_url.startswith('https://')

    def test_shorts_to_dict(self, yt: YouTube):
        result = yt.get_channel_shorts(LEX_CHANNEL_ID)
        d = result.to_dict()

        assert d['channel_id'] == LEX_CHANNEL_ID
        assert isinstance(d['shorts'], list)
        if d['shorts']:
            s = d['shorts'][0]
            assert 'video_id' in s
            assert 'title' in s
            assert 'url' in s

    def test_shorts_json_serializable(self, yt: YouTube):
        result = yt.get_channel_shorts(LEX_CHANNEL_ID)
        json_str = json.dumps(result.to_dict(), ensure_ascii=False)
        assert len(json_str) > 10


# ════════════════════════════════════════════════════════════════
# 4.  CHANNEL PLAYLISTS
# ════════════════════════════════════════════════════════════════


class TestChannelPlaylists:
    """Browse a channel's Playlists tab."""

    def test_get_playlists_by_id(self, yt: YouTube):
        result = yt.get_channel_playlists(LEX_CHANNEL_ID)

        assert isinstance(result, ChannelPlaylistsResult)
        assert result.channel_id == LEX_CHANNEL_ID
        assert len(result.playlists) >= 1

    def test_get_playlists_by_handle(self, yt: YouTube):
        result = yt.get_channel_playlists(LEX_HANDLE)

        assert isinstance(result, ChannelPlaylistsResult)
        assert result.channel_id == LEX_CHANNEL_ID

    def test_playlist_entry_fields(self, yt: YouTube):
        result = yt.get_channel_playlists(LEX_CHANNEL_ID)

        for pl in result.playlists:
            assert isinstance(pl, ChannelPlaylistEntry)
            assert pl.playlist_id
            assert pl.playlist_id.startswith('PL')
            assert pl.title
            assert pl.url == f'https://www.youtube.com/playlist?list={pl.playlist_id}'

    def test_playlists_to_dict(self, yt: YouTube):
        result = yt.get_channel_playlists(LEX_CHANNEL_ID)
        d = result.to_dict()

        assert d['channel_id'] == LEX_CHANNEL_ID
        assert isinstance(d['playlists'], list)
        if d['playlists']:
            p = d['playlists'][0]
            assert 'playlist_id' in p
            assert 'title' in p
            assert 'url' in p


# ════════════════════════════════════════════════════════════════
# 5.  CHANNEL SEARCH
# ════════════════════════════════════════════════════════════════


class TestChannelSearch:
    """Search within a channel's videos."""

    def test_search_by_id(self, yt: YouTube):
        result = yt.search_channel(LEX_CHANNEL_ID, 'artificial intelligence')

        assert isinstance(result, SearchResult)
        assert result.query == 'artificial intelligence'
        assert len(result.videos) >= 1

    def test_search_by_handle(self, yt: YouTube):
        result = yt.search_channel(LEX_HANDLE, 'podcast')

        assert isinstance(result, SearchResult)
        assert len(result.videos) >= 1

    def test_search_result_fields(self, yt: YouTube):
        result = yt.search_channel(LEX_CHANNEL_ID, 'Elon')

        for video in result.videos:
            assert isinstance(video, VideoResult)
            assert len(video.video_id) == 11
            assert video.title
            assert video.url.startswith('https://www.youtube.com/watch?v=')

    def test_search_to_dict(self, yt: YouTube):
        result = yt.search_channel(LEX_CHANNEL_ID, 'science')
        d = result.to_dict()

        assert d['query'] == 'science'
        assert isinstance(d['videos'], list)


# ════════════════════════════════════════════════════════════════
# 6.  PLAYLISTS
# ════════════════════════════════════════════════════════════════


class TestPlaylist:
    """Fetch videos from a YouTube playlist."""

    def test_by_playlist_id(self, yt: YouTube):
        result = yt.get_playlist(LEX_PLAYLIST_ID)

        assert isinstance(result, PlaylistResult)
        assert result.playlist_id == LEX_PLAYLIST_ID
        assert len(result.videos) >= 1

    def test_by_full_url(self, yt: YouTube):
        url = f'https://www.youtube.com/playlist?list={LEX_PLAYLIST_ID}'
        result = yt.get_playlist(url)

        assert result.playlist_id == LEX_PLAYLIST_ID
        assert len(result.videos) >= 1

    def test_playlist_metadata(self, yt: YouTube):
        result = yt.get_playlist(LEX_PLAYLIST_ID)

        assert result.url == f'https://www.youtube.com/playlist?list={LEX_PLAYLIST_ID}'
        # title may or may not be populated depending on YouTube response
        # but we can check it doesn't crash

    def test_playlist_video_fields(self, yt: YouTube):
        result = yt.get_playlist(LEX_PLAYLIST_ID)

        for video in result.videos:
            assert isinstance(video, PlaylistEntry)
            assert len(video.video_id) == 11
            assert video.title
            assert video.url.startswith('https://www.youtube.com/watch?v=')
            assert isinstance(video.duration_seconds, int)

    def test_playlist_videos_have_thumbnails(self, yt: YouTube):
        result = yt.get_playlist(LEX_PLAYLIST_ID)
        with_thumbs = [v for v in result.videos if v.thumbnails]
        assert len(with_thumbs) >= 1

        for video in with_thumbs:
            assert video.thumbnail_url is not None
            assert video.thumbnail_url.startswith('https://')

    def test_playlist_max_results(self, yt: YouTube):
        result = yt.get_playlist(LEX_PLAYLIST_ID, max_results=3)
        assert len(result.videos) <= 3

    def test_playlist_to_dict(self, yt: YouTube):
        result = yt.get_playlist(LEX_PLAYLIST_ID, max_results=3)
        d = result.to_dict()

        assert d['playlist_id'] == LEX_PLAYLIST_ID
        assert isinstance(d['videos'], list)
        assert 'url' in d
        if d['videos']:
            v = d['videos'][0]
            assert 'video_id' in v

    def test_playlist_json_serializable(self, yt: YouTube):
        result = yt.get_playlist(LEX_PLAYLIST_ID, max_results=3)
        json_str = json.dumps(result.to_dict(), ensure_ascii=False)
        parsed = json.loads(json_str)
        assert parsed['playlist_id'] == LEX_PLAYLIST_ID


# ════════════════════════════════════════════════════════════════
# 7.  TRANSCRIPTS
# ════════════════════════════════════════════════════════════════


class TestTranscript:
    """Fetch, list, translate, format, and save transcripts."""

    # ── Fetch ──

    def test_fetch_by_video_id(self, yt: YouTube):
        transcript = yt.get_transcript(RICK_VIDEO_ID)

        assert isinstance(transcript, Transcript)
        assert transcript.video_id == RICK_VIDEO_ID
        assert transcript.language
        assert transcript.language_code
        assert isinstance(transcript.is_generated, bool)
        assert len(transcript.segments) > 0

    def test_fetch_by_full_url(self, yt: YouTube):
        transcript = yt.get_transcript(
            f'https://www.youtube.com/watch?v={RICK_VIDEO_ID}',
        )
        assert transcript.video_id == RICK_VIDEO_ID
        assert len(transcript.segments) > 0

    def test_fetch_by_short_url(self, yt: YouTube):
        transcript = yt.get_transcript(f'https://youtu.be/{RICK_VIDEO_ID}')
        assert transcript.video_id == RICK_VIDEO_ID

    def test_fetch_with_language(self, yt: YouTube):
        transcript = yt.get_transcript(RICK_VIDEO_ID, languages=['en'])

        assert transcript.language_code == 'en'
        assert len(transcript.segments) > 0

    # ── Segment fields ──

    def test_segment_fields(self, yt: YouTube):
        transcript = yt.get_transcript(RICK_VIDEO_ID)

        for segment in transcript.segments[:5]:
            assert isinstance(segment, TranscriptSegment)
            assert isinstance(segment.text, str)
            assert len(segment.text) > 0
            assert isinstance(segment.start, float)
            assert segment.start >= 0.0
            assert isinstance(segment.duration, float)
            assert segment.duration >= 0.0

    def test_segments_ordered_by_start(self, yt: YouTube):
        transcript = yt.get_transcript(RICK_VIDEO_ID)
        starts = [s.start for s in transcript.segments]
        assert starts == sorted(starts), 'Segments should be ordered by start time'

    # ── Text property ──

    def test_text_property(self, yt: YouTube):
        transcript = yt.get_transcript(RICK_VIDEO_ID)

        text = transcript.text
        assert isinstance(text, str)
        assert len(text) > 50, 'Full transcript text should be substantial'

    # ── Without timestamps ──

    def test_without_timestamps(self, yt: YouTube):
        transcript = yt.get_transcript(RICK_VIDEO_ID, timestamps=False)

        # Should still have segments, but collapsed into one
        assert len(transcript.segments) == 1
        assert transcript.segments[0].start == 0.0
        assert transcript.segments[0].duration == 0.0
        assert len(transcript.text) > 50

    def test_without_timestamps_method(self, yt: YouTube):
        transcript = yt.get_transcript(RICK_VIDEO_ID)
        plain = transcript.without_timestamps()

        assert len(plain.segments) == 1
        assert plain.video_id == RICK_VIDEO_ID
        assert plain.language == transcript.language

    # ── List transcripts ──

    def test_list_transcripts(self, yt: YouTube):
        entries = yt.list_transcripts(RICK_VIDEO_ID)

        assert isinstance(entries, list)
        assert len(entries) >= 1

        for entry in entries:
            assert isinstance(entry, TranscriptListEntry)
            assert entry.language
            assert entry.language_code
            assert isinstance(entry.is_generated, bool)
            assert isinstance(entry.is_translatable, bool)

    def test_list_transcripts_has_english(self, yt: YouTube):
        entries = yt.list_transcripts(RICK_VIDEO_ID)
        codes = [e.language_code for e in entries]
        assert 'en' in codes, f'Expected "en" in {codes}'

    def test_list_transcripts_by_url(self, yt: YouTube):
        entries = yt.list_transcripts(
            f'https://www.youtube.com/watch?v={RICK_VIDEO_ID}',
        )
        assert len(entries) >= 1

    # ── Translate ──

    def test_translate_to_spanish(self, yt: YouTube):
        transcript = yt.get_transcript(RICK_VIDEO_ID, translate_to='es')

        assert transcript.translation_language == 'es'
        assert len(transcript.segments) > 0
        assert len(transcript.text) > 50

    def test_translate_to_french(self, yt: YouTube):
        transcript = yt.get_transcript(RICK_VIDEO_ID, translate_to='fr')

        assert transcript.translation_language == 'fr'
        assert len(transcript.text) > 50

    def test_translate_invalid_language(self, yt: YouTube):
        with pytest.raises(TranslationNotAvailableError):
            yt.get_transcript(RICK_VIDEO_ID, translate_to='xyz_invalid')

    # ── to_dict ──

    def test_to_dict_with_timestamps(self, yt: YouTube):
        transcript = yt.get_transcript(RICK_VIDEO_ID)
        d = transcript.to_dict()

        assert d['video_id'] == RICK_VIDEO_ID
        assert d['language']
        assert d['language_code']
        assert isinstance(d['is_generated'], bool)
        assert isinstance(d['segments'], list)
        assert len(d['segments']) > 0
        assert 'text' in d['segments'][0]
        assert 'start' in d['segments'][0]
        assert 'duration' in d['segments'][0]
        assert 'text' in d  # full text

    def test_to_dict_without_timestamps(self, yt: YouTube):
        transcript = yt.get_transcript(RICK_VIDEO_ID)
        d = transcript.to_dict(timestamps=False)

        assert 'segments' not in d
        assert 'text' in d
        assert len(d['text']) > 50

    def test_transcript_json_serializable(self, yt: YouTube):
        transcript = yt.get_transcript(RICK_VIDEO_ID)
        json_str = json.dumps(transcript.to_dict(), ensure_ascii=False)
        parsed = json.loads(json_str)
        assert parsed['video_id'] == RICK_VIDEO_ID


# ════════════════════════════════════════════════════════════════
# 8.  TRANSCRIPT FORMATTING
# ════════════════════════════════════════════════════════════════


class TestTranscriptFormatting:
    """Format transcripts to text, JSON, SRT, WebVTT."""

    def test_format_text(self, yt: YouTube):
        transcript = yt.get_transcript(RICK_VIDEO_ID)
        text = YouTube.format_transcript(transcript, fmt='text')

        assert isinstance(text, str)
        assert len(text) > 50

    def test_format_json(self, yt: YouTube):
        transcript = yt.get_transcript(RICK_VIDEO_ID)
        json_str = YouTube.format_transcript(transcript, fmt='json')

        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
        assert 'segments' in parsed
        assert len(parsed['segments']) > 0
        assert 'text' in parsed['segments'][0]

    def test_format_srt(self, yt: YouTube):
        transcript = yt.get_transcript(RICK_VIDEO_ID)
        srt = YouTube.format_transcript(transcript, fmt='srt')

        lines = srt.strip().split('\n')
        assert lines[0] == '1'
        # SRT timestamp: HH:MM:SS,mmm --> HH:MM:SS,mmm
        assert re.match(r'\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}', lines[1])

    def test_format_vtt(self, yt: YouTube):
        transcript = yt.get_transcript(RICK_VIDEO_ID)
        vtt = YouTube.format_transcript(transcript, fmt='vtt')

        assert vtt.startswith('WEBVTT')
        # WebVTT timestamp: HH:MM:SS.mmm --> HH:MM:SS.mmm
        assert re.search(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}', vtt)


# ════════════════════════════════════════════════════════════════
# 9.  TRANSCRIPT SAVE TO FILE
# ════════════════════════════════════════════════════════════════


class TestTranscriptSave:
    """Save transcripts to files in various formats."""

    def test_save_srt(self, yt: YouTube):
        transcript = yt.get_transcript(RICK_VIDEO_ID)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = transcript.save(str(Path(tmpdir) / 'subtitles.srt'))

            assert path.exists()
            assert path.suffix == '.srt'
            content = path.read_text(encoding='utf-8')
            assert '1' in content
            assert '-->' in content

    def test_save_json(self, yt: YouTube):
        transcript = yt.get_transcript(RICK_VIDEO_ID)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = transcript.save(str(Path(tmpdir) / 'output.json'))

            assert path.exists()
            assert path.suffix == '.json'
            parsed = json.loads(path.read_text(encoding='utf-8'))
            assert isinstance(parsed, dict)
            assert 'segments' in parsed
            assert len(parsed['segments']) > 0

    def test_save_vtt(self, yt: YouTube):
        transcript = yt.get_transcript(RICK_VIDEO_ID)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = transcript.save(str(Path(tmpdir) / 'transcript.vtt'))

            assert path.exists()
            assert path.suffix == '.vtt'
            content = path.read_text(encoding='utf-8')
            assert content.startswith('WEBVTT')

    def test_save_txt(self, yt: YouTube):
        transcript = yt.get_transcript(RICK_VIDEO_ID)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = transcript.save(str(Path(tmpdir) / 'transcript.txt'))

            assert path.exists()
            assert path.suffix == '.txt'
            content = path.read_text(encoding='utf-8')
            assert len(content) > 50

    def test_save_with_explicit_format(self, yt: YouTube):
        transcript = yt.get_transcript(RICK_VIDEO_ID)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = transcript.save(str(Path(tmpdir) / 'output'), format='srt')

            assert path.exists()
            assert path.suffix == '.srt'

    def test_save_invalid_format_raises(self, yt: YouTube):
        transcript = yt.get_transcript(RICK_VIDEO_ID)

        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError):
                transcript.save(str(Path(tmpdir) / 'output.xyz'))


# ════════════════════════════════════════════════════════════════
# 10. URL PARSING
# ════════════════════════════════════════════════════════════════


class TestURLParsing:
    """Static URL parsing methods on the YouTube class."""

    # ── Video IDs ──

    def test_extract_video_id_plain(self):
        assert YouTube.extract_video_id('dQw4w9WgXcQ') == 'dQw4w9WgXcQ'

    def test_extract_video_id_watch_url(self):
        assert YouTube.extract_video_id(
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        ) == 'dQw4w9WgXcQ'

    def test_extract_video_id_short_url(self):
        assert YouTube.extract_video_id('https://youtu.be/dQw4w9WgXcQ') == 'dQw4w9WgXcQ'

    def test_extract_video_id_embed(self):
        assert YouTube.extract_video_id(
            'https://www.youtube.com/embed/dQw4w9WgXcQ'
        ) == 'dQw4w9WgXcQ'

    def test_extract_video_id_shorts(self):
        assert YouTube.extract_video_id(
            'https://www.youtube.com/shorts/dQw4w9WgXcQ'
        ) == 'dQw4w9WgXcQ'

    def test_extract_video_id_live(self):
        assert YouTube.extract_video_id(
            'https://www.youtube.com/live/dQw4w9WgXcQ'
        ) == 'dQw4w9WgXcQ'

    def test_extract_video_id_mobile(self):
        assert YouTube.extract_video_id(
            'https://m.youtube.com/watch?v=dQw4w9WgXcQ'
        ) == 'dQw4w9WgXcQ'

    def test_extract_video_id_with_extra_params(self):
        assert YouTube.extract_video_id(
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s&list=PLtest'
        ) == 'dQw4w9WgXcQ'

    def test_extract_video_id_invalid(self):
        with pytest.raises(ValueError):
            YouTube.extract_video_id('not-a-video-id')

    # ── Channel IDs ──

    def test_extract_channel_id_plain(self):
        assert YouTube.extract_channel_id(LEX_CHANNEL_ID) == LEX_CHANNEL_ID

    def test_extract_channel_id_url(self):
        assert YouTube.extract_channel_id(
            f'https://www.youtube.com/channel/{LEX_CHANNEL_ID}'
        ) == LEX_CHANNEL_ID

    def test_extract_channel_id_handle(self):
        result = YouTube.extract_channel_id(LEX_HANDLE)
        assert result == LEX_HANDLE

    def test_extract_channel_id_handle_url(self):
        result = YouTube.extract_channel_id(f'https://www.youtube.com/{LEX_HANDLE}')
        assert result == LEX_HANDLE

    def test_extract_channel_id_invalid(self):
        with pytest.raises(ValueError):
            YouTube.extract_channel_id('not-a-channel')

    # ── Playlist IDs ──

    def test_extract_playlist_id_plain(self):
        assert YouTube.extract_playlist_id(LEX_PLAYLIST_ID) == LEX_PLAYLIST_ID

    def test_extract_playlist_id_url(self):
        assert YouTube.extract_playlist_id(
            f'https://www.youtube.com/playlist?list={LEX_PLAYLIST_ID}'
        ) == LEX_PLAYLIST_ID

    def test_extract_playlist_id_watch_url(self):
        assert YouTube.extract_playlist_id(
            f'https://www.youtube.com/watch?v=abc123&list={LEX_PLAYLIST_ID}'
        ) == LEX_PLAYLIST_ID

    def test_extract_playlist_id_invalid(self):
        with pytest.raises(ValueError):
            YouTube.extract_playlist_id('not-a-playlist')


# ════════════════════════════════════════════════════════════════
# 11. ERROR HANDLING
# ════════════════════════════════════════════════════════════════


class TestErrorHandling:
    """Verify correct exceptions for invalid/unavailable resources."""

    def test_unavailable_video_transcript(self, yt: YouTube):
        with pytest.raises((VideoUnavailableError, TranscriptsDisabledError, YouTubeError)):
            yt.get_transcript('xxxxxxxxxxx')  # likely not a real video

    def test_invalid_channel(self, yt: YouTube):
        with pytest.raises((ChannelNotFoundError, YouTubeError)):
            yt.get_channel_videos('@absolutelynotarealperson_zzz_999')

    def test_translation_not_available(self, yt: YouTube):
        with pytest.raises(TranslationNotAvailableError):
            yt.get_transcript(RICK_VIDEO_ID, translate_to='xyz_nonexistent')

    def test_youtube_error_is_base(self):
        """All custom exceptions should inherit from YouTubeError."""
        assert issubclass(VideoUnavailableError, YouTubeError)
        assert issubclass(ChannelNotFoundError, YouTubeError)
        assert issubclass(PlaylistNotFoundError, YouTubeError)
        assert issubclass(TranscriptsDisabledError, YouTubeError)
        assert issubclass(TranslationNotAvailableError, YouTubeError)

    def test_url_parsing_errors_are_value_error(self):
        with pytest.raises(ValueError):
            YouTube.extract_video_id('')
        with pytest.raises(ValueError):
            YouTube.extract_playlist_id('')


# ════════════════════════════════════════════════════════════════
# 12. CONTEXT MANAGER
# ════════════════════════════════════════════════════════════════


class TestContextManager:
    """Test sync and async context manager support."""

    def test_sync_context_manager(self):
        with YouTube() as yt:
            result = yt.search('test', max_results=1)
            assert len(result.videos) >= 1

    def test_async_context_manager(self):
        async def run():
            async with YouTube() as yt:
                result = await yt.asearch('test', max_results=1)
                assert len(result.videos) >= 1

        asyncio.run(run())


# ════════════════════════════════════════════════════════════════
# 13. ASYNC METHODS
# ════════════════════════════════════════════════════════════════


class TestAsync:
    """Verify all async method variants work end-to-end."""

    def test_async_search(self):
        async def run():
            async with YouTube() as yt:
                result = await yt.asearch('python', max_results=3)
                assert len(result.videos) >= 1

        asyncio.run(run())

    def test_async_channel_videos(self):
        async def run():
            async with YouTube() as yt:
                result = await yt.aget_channel_videos(LEX_CHANNEL_ID, max_results=3)
                assert len(result.videos) >= 1

        asyncio.run(run())

    def test_async_channel_shorts(self):
        async def run():
            async with YouTube() as yt:
                result = await yt.aget_channel_shorts(LEX_CHANNEL_ID)
                assert len(result.shorts) >= 1

        asyncio.run(run())

    def test_async_channel_playlists(self):
        async def run():
            async with YouTube() as yt:
                result = await yt.aget_channel_playlists(LEX_CHANNEL_ID)
                assert len(result.playlists) >= 1

        asyncio.run(run())

    def test_async_channel_search(self):
        async def run():
            async with YouTube() as yt:
                result = await yt.asearch_channel(LEX_CHANNEL_ID, 'podcast')
                assert len(result.videos) >= 1

        asyncio.run(run())

    def test_async_playlist(self):
        async def run():
            async with YouTube() as yt:
                result = await yt.aget_playlist(LEX_PLAYLIST_ID, max_results=3)
                assert len(result.videos) >= 1

        asyncio.run(run())

    def test_async_transcript(self):
        async def run():
            async with YouTube() as yt:
                transcript = await yt.aget_transcript(RICK_VIDEO_ID)
                assert len(transcript.segments) > 0

        asyncio.run(run())

    def test_async_list_transcripts(self):
        async def run():
            async with YouTube() as yt:
                entries = await yt.alist_transcripts(RICK_VIDEO_ID)
                assert len(entries) >= 1

        asyncio.run(run())

    def test_async_translate(self):
        async def run():
            async with YouTube() as yt:
                transcript = await yt.aget_transcript(RICK_VIDEO_ID, translate_to='de')
                assert transcript.translation_language == 'de'

        asyncio.run(run())


# ════════════════════════════════════════════════════════════════
# 14. CROSS-FEATURE WORKFLOWS
# ════════════════════════════════════════════════════════════════


class TestWorkflows:
    """End-to-end workflows combining multiple features."""

    def test_search_then_transcript(self, yt: YouTube):
        """Search for a video, then fetch its transcript."""
        results = yt.search('Rick Astley Never Gonna Give You Up', max_results=3)
        assert len(results.videos) >= 1

        # Find the Rick Astley video
        target = None
        for video in results.videos:
            if 'rick' in video.title.lower() or video.video_id == RICK_VIDEO_ID:
                target = video
                break

        if target:
            transcript = yt.get_transcript(target.video_id)
            assert len(transcript.segments) > 0

    def test_channel_videos_then_transcript(self, yt: YouTube):
        """Get a channel's videos, then fetch transcript for the first one."""
        videos = yt.get_channel_videos(LEX_CHANNEL_ID, max_results=3)
        assert len(videos.videos) >= 1

        first = videos.videos[0]
        try:
            transcript = yt.get_transcript(first.video_id)
            assert transcript.video_id == first.video_id
            assert len(transcript.segments) > 0
        except (TranscriptsDisabledError, TranscriptsNotAvailableError):
            pass  # Some videos may not have transcripts

    def test_channel_playlists_then_fetch(self, yt: YouTube):
        """Get a channel's playlists, then fetch videos from the first one."""
        playlists = yt.get_channel_playlists(LEX_CHANNEL_ID)
        assert len(playlists.playlists) >= 1

        first_pl = playlists.playlists[0]
        result = yt.get_playlist(first_pl.playlist_id, max_results=3)
        assert result.playlist_id == first_pl.playlist_id
        assert len(result.videos) >= 1

    def test_search_filter_and_serialize(self, yt: YouTube):
        """Search with filters, then serialize the entire result to JSON."""
        result = yt.search(
            'cooking recipe',
            type='video',
            duration='medium',
            max_results=3,
        )
        d = result.to_dict()
        json_str = json.dumps(d, ensure_ascii=False, indent=2)
        parsed = json.loads(json_str)

        assert parsed['query'] == 'cooking recipe'
        assert isinstance(parsed['videos'], list)

    def test_transcript_fetch_format_save(self, yt: YouTube):
        """Fetch a transcript, format it to SRT, and save to file."""
        transcript = yt.get_transcript(RICK_VIDEO_ID)

        # Format to all types
        for fmt in ('text', 'json', 'srt', 'vtt'):
            formatted = YouTube.format_transcript(transcript, fmt=fmt)
            assert isinstance(formatted, str)
            assert len(formatted) > 10

        # Save to temp file
        with tempfile.TemporaryDirectory() as tmpdir:
            path = transcript.save(str(Path(tmpdir) / 'rick.srt'))
            assert path.exists()
            content = path.read_text(encoding='utf-8')
            assert '-->' in content

    def test_full_channel_exploration(self, yt: YouTube):
        """Browse all tabs of a channel: videos, shorts, playlists, search."""
        # Videos
        videos = yt.get_channel_videos(LEX_CHANNEL_ID, max_results=2)
        assert len(videos.videos) >= 1

        # Shorts
        shorts = yt.get_channel_shorts(LEX_CHANNEL_ID)
        assert isinstance(shorts, ShortsResult)

        # Playlists
        playlists = yt.get_channel_playlists(LEX_CHANNEL_ID)
        assert isinstance(playlists, ChannelPlaylistsResult)

        # Search
        search = yt.search_channel(LEX_CHANNEL_ID, 'AI')
        assert isinstance(search, SearchResult)

    def test_video_result_sparse_to_dict(self, yt: YouTube):
        """Verify that to_dict() is sparse — optional fields excluded when default."""
        result = yt.search('test', max_results=1)
        if not result.videos:
            pytest.skip('No search results')

        d = result.videos[0].to_dict()

        # Core fields always present
        assert 'video_id' in d
        assert 'title' in d
        assert 'url' in d
        assert 'is_live' in d

        # Optional fields only present when populated
        if result.videos[0].is_verified is False:
            assert 'is_verified' not in d
        if not result.videos[0].badges:
            assert 'badges' not in d
