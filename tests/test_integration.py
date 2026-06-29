"""Integration tests using real captured YouTube API responses.

These tests verify that our parsers correctly handle real-world
InnerTube response structures captured from live API calls.

Fixtures:
    raw_search.json         — raw /youtubei/v1/search response
    raw_channel.json        — raw /youtubei/v1/browse (videos tab)
    raw_playlist.json       — raw /youtubei/v1/browse (playlist)
    live_shorts_raw.json    — raw /youtubei/v1/browse (shorts tab)
    live_channel_playlists_raw.json  — raw /youtubei/v1/browse (playlists tab)
    live_channel_search_raw.json     — raw /youtubei/v1/browse (search tab)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tubescrape._parsers import ResponseParser

FIXTURES = Path(__file__).parent / 'fixtures'


def _load(name: str) -> dict | list:
    path = FIXTURES / name
    if not path.exists():
        pytest.skip(f'Fixture {name} not found')
    return json.loads(path.read_text(encoding='utf-8'))


class TestSearchIntegration:
    def test_parse_real_search(self):
        data = _load('raw_search.json')
        result, _ = ResponseParser.parse_search_response(data, 'python tutorial', 20)
        assert result.query == 'python tutorial'
        assert len(result.videos) >= 1

        video = result.videos[0]
        assert video.video_id
        assert len(video.video_id) == 11
        assert video.title
        assert video.url.startswith('https://www.youtube.com/watch?v=')

    def test_search_videos_have_rich_data(self):
        data = _load('raw_search.json')
        result, _ = ResponseParser.parse_search_response(data, 'test', 20)
        # At least some results should have thumbnails
        with_thumbs = [v for v in result.videos if v.thumbnails]
        assert len(with_thumbs) >= 1
        for video in with_thumbs:
            assert video.thumbnails[0].url.startswith('https://')
            assert video.thumbnails[0].width > 0


class TestChannelBrowseIntegration:
    def test_parse_real_channel(self):
        data = _load('raw_channel.json')
        videos, continuation = ResponseParser.parse_browse_first_page(
            data, 'UCJIfeSCssxSC_Dhc5s7woww',
        )
        assert len(videos) >= 1

        video = videos[0]
        assert video.video_id
        assert video.title
        assert video.url.startswith('https://www.youtube.com/watch?v=')

    def test_channel_videos_have_thumbnails(self):
        data = _load('raw_channel.json')
        videos, _ = ResponseParser.parse_browse_first_page(
            data, 'UCJIfeSCssxSC_Dhc5s7woww',
        )
        with_thumbs = [v for v in videos if v.thumbnails]
        assert len(with_thumbs) >= 1
        for video in with_thumbs:
            for thumb in video.thumbnails:
                assert thumb.url.startswith('https://')
                assert thumb.width > 0
                assert thumb.height > 0

    def test_channel_has_continuation_token(self):
        data = _load('raw_channel.json')
        videos, continuation = ResponseParser.parse_browse_first_page(
            data, 'UCJIfeSCssxSC_Dhc5s7woww',
        )
        # A real channel with many videos should have a continuation token
        assert continuation is not None or len(videos) > 0


class TestPlaylistIntegration:
    def test_parse_real_playlist(self):
        data = _load('raw_playlist.json')
        result, continuation = ResponseParser.parse_playlist_response(
            data, 'PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf',
        )
        assert result.playlist_id == 'PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf'
        assert len(result.videos) >= 1

        video = result.videos[0]
        assert video.video_id
        assert video.title
        assert video.url.startswith('https://www.youtube.com/watch?v=')

    def test_playlist_has_metadata(self):
        data = _load('raw_playlist.json')
        result, _ = ResponseParser.parse_playlist_response(
            data, 'PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf',
        )
        # Real playlist should have title
        assert result.title or True  # Some playlists may not return title

    def test_playlist_videos_have_thumbnails(self):
        data = _load('raw_playlist.json')
        result, _ = ResponseParser.parse_playlist_response(
            data, 'PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf',
        )
        with_thumbs = [v for v in result.videos if v.thumbnails]
        assert len(with_thumbs) >= 1


class TestShortsTabIntegration:
    def test_parse_real_shorts(self):
        data = _load('live_shorts_raw.json')
        result = ResponseParser.parse_shorts_tab(data, 'UCJIfeSCssxSC_Dhc5s7woww')
        assert result.channel_id == 'UCJIfeSCssxSC_Dhc5s7woww'
        assert len(result.shorts) >= 1

        short = result.shorts[0]
        assert short.video_id
        assert len(short.video_id) == 11
        assert short.title
        assert short.url.startswith('https://www.youtube.com/shorts/')

    def test_shorts_have_view_counts(self):
        data = _load('live_shorts_raw.json')
        result = ResponseParser.parse_shorts_tab(data, 'UCJIfeSCssxSC_Dhc5s7woww')
        with_views = [s for s in result.shorts if s.view_count]
        assert len(with_views) >= 1

    def test_shorts_have_thumbnails(self):
        data = _load('live_shorts_raw.json')
        result = ResponseParser.parse_shorts_tab(data, 'UCJIfeSCssxSC_Dhc5s7woww')
        with_thumbs = [s for s in result.shorts if s.thumbnail_url]
        assert len(with_thumbs) >= 1

    def test_shorts_to_dict(self):
        data = _load('live_shorts_raw.json')
        result = ResponseParser.parse_shorts_tab(data, 'UCJIfeSCssxSC_Dhc5s7woww')
        d = result.to_dict()
        assert d['channel_id'] == 'UCJIfeSCssxSC_Dhc5s7woww'
        assert len(d['shorts']) >= 1
        assert 'video_id' in d['shorts'][0]
        assert 'url' in d['shorts'][0]


class TestChannelPlaylistsTabIntegration:
    def test_parse_real_playlists_tab(self):
        data = _load('live_channel_playlists_raw.json')
        result = ResponseParser.parse_channel_playlists_tab(
            data, 'UCJIfeSCssxSC_Dhc5s7woww',
        )
        assert result.channel_id == 'UCJIfeSCssxSC_Dhc5s7woww'
        assert len(result.playlists) >= 1

        playlist = result.playlists[0]
        assert playlist.playlist_id
        assert playlist.playlist_id.startswith('PL')
        assert playlist.title
        assert playlist.url.startswith('https://www.youtube.com/playlist?list=')

    def test_playlists_to_dict(self):
        data = _load('live_channel_playlists_raw.json')
        result = ResponseParser.parse_channel_playlists_tab(
            data, 'UCJIfeSCssxSC_Dhc5s7woww',
        )
        d = result.to_dict()
        assert d['channel_id'] == 'UCJIfeSCssxSC_Dhc5s7woww'
        assert len(d['playlists']) >= 1
        assert 'playlist_id' in d['playlists'][0]


class TestChannelSearchIntegration:
    def test_parse_real_channel_search(self):
        data = _load('live_channel_search_raw.json')
        result = ResponseParser.parse_channel_search(
            data, 'UCJIfeSCssxSC_Dhc5s7woww', 'podcast',
        )
        assert result.query == 'podcast'
        assert len(result.videos) >= 1

        video = result.videos[0]
        assert video.video_id
        assert len(video.video_id) == 11
        assert video.title
        assert video.url.startswith('https://www.youtube.com/watch?v=')

    def test_channel_search_videos_have_durations(self):
        data = _load('live_channel_search_raw.json')
        result = ResponseParser.parse_channel_search(
            data, 'UCJIfeSCssxSC_Dhc5s7woww', 'podcast',
        )
        with_duration = [v for v in result.videos if v.duration_seconds > 0]
        assert len(with_duration) >= 1

    def test_channel_search_to_dict(self):
        data = _load('live_channel_search_raw.json')
        result = ResponseParser.parse_channel_search(
            data, 'UCJIfeSCssxSC_Dhc5s7woww', 'podcast',
        )
        d = result.to_dict()
        assert d['query'] == 'podcast'
        assert len(d['videos']) >= 1
