from __future__ import annotations

from tubescrape._parsers import ResponseParser


class TestParsePlaylistResponse:
    """Test playlist response parsing."""

    def test_valid_playlist(self):
        data = {
            'header': {
                'playlistHeaderRenderer': {
                    'title': {'simpleText': 'My Playlist'},
                    'ownerText': {'simpleText': 'Test Channel'},
                }
            },
            'contents': {
                'twoColumnBrowseResultsRenderer': {
                    'tabs': [{
                        'tabRenderer': {
                            'content': {
                                'sectionListRenderer': {
                                    'contents': [{
                                        'itemSectionRenderer': {
                                            'contents': [{
                                                'playlistVideoListRenderer': {
                                                    'contents': [
                                                        {
                                                            'playlistVideoRenderer': {
                                                                'videoId': 'vid1',
                                                                'title': {'simpleText': 'Video 1'},
                                                                'shortBylineText': {'simpleText': 'Channel 1'},
                                                                'lengthText': {'simpleText': '5:00'},
                                                                'index': {'simpleText': '1'},
                                                            }
                                                        },
                                                        {
                                                            'playlistVideoRenderer': {
                                                                'videoId': 'vid2',
                                                                'title': {'simpleText': 'Video 2'},
                                                                'shortBylineText': {'simpleText': 'Channel 2'},
                                                                'lengthText': {'simpleText': '10:30'},
                                                                'index': {'simpleText': '2'},
                                                            }
                                                        },
                                                    ]
                                                }
                                            }]
                                        }
                                    }]
                                }
                            }
                        }
                    }]
                }
            },
        }
        result, continuation = ResponseParser.parse_playlist_response(data, 'PL123')
        assert result.playlist_id == 'PL123'
        assert result.title == 'My Playlist'
        assert result.channel == 'Test Channel'
        assert len(result.videos) == 2
        assert result.videos[0].video_id == 'vid1'
        assert result.videos[0].title == 'Video 1'
        assert result.videos[0].duration_seconds == 300
        assert result.videos[1].video_id == 'vid2'
        assert continuation is None

    def test_empty_playlist(self):
        result, continuation = ResponseParser.parse_playlist_response({}, 'PL123')
        assert result.playlist_id == 'PL123'
        assert result.videos == []
        assert continuation is None

    def test_continuation_token(self):
        data = {
            'header': {},
            'contents': {
                'twoColumnBrowseResultsRenderer': {
                    'tabs': [{
                        'tabRenderer': {
                            'content': {
                                'sectionListRenderer': {
                                    'contents': [{
                                        'itemSectionRenderer': {
                                            'contents': [{
                                                'playlistVideoListRenderer': {
                                                    'contents': [
                                                        {
                                                            'playlistVideoRenderer': {
                                                                'videoId': 'vid1',
                                                                'title': {'simpleText': 'V1'},
                                                                'shortBylineText': {'simpleText': 'C1'},
                                                                'lengthText': {'simpleText': '1:00'},
                                                                'index': {'simpleText': '1'},
                                                            }
                                                        },
                                                        {
                                                            'continuationItemRenderer': {
                                                                'continuationEndpoint': {
                                                                    'continuationCommand': {
                                                                        'token': 'NEXT_TOKEN'
                                                                    }
                                                                }
                                                            }
                                                        },
                                                    ]
                                                }
                                            }]
                                        }
                                    }]
                                }
                            }
                        }
                    }]
                }
            },
        }
        result, continuation = ResponseParser.parse_playlist_response(data, 'PL123')
        assert len(result.videos) == 1
        assert continuation == 'NEXT_TOKEN'


class TestParsePlaylistContinuation:
    """Test playlist continuation response parsing."""

    def test_valid_continuation(self):
        data = {
            'onResponseReceivedActions': [{
                'appendContinuationItemsAction': {
                    'continuationItems': [
                        {
                            'playlistVideoRenderer': {
                                'videoId': 'vid3',
                                'title': {'simpleText': 'Video 3'},
                                'shortBylineText': {'simpleText': 'Channel 3'},
                                'lengthText': {'simpleText': '7:00'},
                                'index': {'simpleText': '3'},
                            }
                        },
                    ]
                }
            }]
        }
        videos, continuation = ResponseParser.parse_playlist_continuation(data)
        assert len(videos) == 1
        assert videos[0].video_id == 'vid3'
        assert continuation is None

    def test_empty_continuation(self):
        videos, continuation = ResponseParser.parse_playlist_continuation({})
        assert videos == []
        assert continuation is None


class TestParsePlaylistVideo:
    """Test individual playlist video parsing."""

    def test_valid_video(self):
        renderer = {
            'videoId': 'abc123',
            'title': {'simpleText': 'Test'},
            'shortBylineText': {'simpleText': 'Channel'},
            'lengthText': {'simpleText': '3:30'},
            'index': {'simpleText': '5'},
        }
        entry = ResponseParser._parse_playlist_video(renderer)
        assert entry is not None
        assert entry.video_id == 'abc123'
        assert entry.title == 'Test'
        assert entry.channel == 'Channel'
        assert entry.duration == '3:30'
        assert entry.duration_seconds == 210
        assert entry.url == 'https://www.youtube.com/watch?v=abc123'

    def test_no_video_id(self):
        assert ResponseParser._parse_playlist_video({}) is None

    def test_minimal_video(self):
        renderer = {
            'videoId': 'abc123',
            'title': {'simpleText': 'Test'},
            'shortBylineText': {'simpleText': 'Channel'},
            'lengthText': {'simpleText': '1:00'},
        }
        entry = ResponseParser._parse_playlist_video(renderer)
        assert entry.video_id == 'abc123'
