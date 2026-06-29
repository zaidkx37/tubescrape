from __future__ import annotations

from tubescrape._parsers import ResponseParser


class TestGetText:
    def test_simple_text(self):
        assert ResponseParser.get_text({'simpleText': 'hello'}) == 'hello'

    def test_runs(self):
        obj = {'runs': [{'text': 'hello '}, {'text': 'world'}]}
        assert ResponseParser.get_text(obj) == 'hello world'

    def test_none(self):
        assert ResponseParser.get_text(None) == ''

    def test_empty_dict(self):
        assert ResponseParser.get_text({}) == ''


class TestParseDuration:
    def test_minutes_seconds(self):
        assert ResponseParser.parse_duration('23:45') == 23 * 60 + 45

    def test_hours_minutes_seconds(self):
        assert ResponseParser.parse_duration('1:23:45') == 1 * 3600 + 23 * 60 + 45

    def test_empty(self):
        assert ResponseParser.parse_duration('') == 0

    def test_invalid(self):
        assert ResponseParser.parse_duration('abc') == 0

    def test_short(self):
        assert ResponseParser.parse_duration('0:30') == 30


class TestExtractChannelId:
    def test_valid_renderer(self):
        renderer = {
            'ownerText': {
                'runs': [{
                    'text': 'Test Channel',
                    'navigationEndpoint': {
                        'browseEndpoint': {'browseId': 'UC123'}
                    },
                }]
            }
        }
        assert ResponseParser.extract_channel_id(renderer) == 'UC123'

    def test_missing_data(self):
        assert ResponseParser.extract_channel_id({}) is None

    def test_no_runs(self):
        assert ResponseParser.extract_channel_id({'ownerText': {}}) is None


class TestExtractTimeStatusStyle:
    def test_live(self):
        renderer = {
            'thumbnailOverlays': [{
                'thumbnailOverlayTimeStatusRenderer': {'style': 'LIVE'}
            }]
        }
        assert ResponseParser.extract_time_status_style(renderer) == 'LIVE'

    def test_no_overlays(self):
        assert ResponseParser.extract_time_status_style({}) == ''


class TestExtractThumbnails:
    def test_valid_thumbnails(self):
        renderer = {
            'thumbnail': {
                'thumbnails': [
                    {'url': 'https://i.ytimg.com/vi/abc/hq360.jpg', 'width': 360, 'height': 202},
                    {'url': 'https://i.ytimg.com/vi/abc/hq720.jpg', 'width': 720, 'height': 404},
                ]
            }
        }
        thumbs = ResponseParser.extract_thumbnails(renderer)
        assert len(thumbs) == 2
        assert thumbs[0].url == 'https://i.ytimg.com/vi/abc/hq360.jpg'
        assert thumbs[0].width == 360
        assert thumbs[0].height == 202
        assert thumbs[1].width == 720

    def test_no_thumbnails(self):
        assert ResponseParser.extract_thumbnails({}) == []

    def test_empty_thumbnail_list(self):
        assert ResponseParser.extract_thumbnails({'thumbnail': {'thumbnails': []}}) == []


class TestExtractMovingThumbnail:
    def test_valid(self):
        renderer = {
            'richThumbnail': {
                'movingThumbnailRenderer': {
                    'movingThumbnailDetails': {
                        'thumbnails': [
                            {'url': 'https://i.ytimg.com/an_webp/abc/mqdefault_6s.webp', 'width': 320, 'height': 180}
                        ]
                    }
                }
            }
        }
        assert ResponseParser.extract_moving_thumbnail(renderer) == 'https://i.ytimg.com/an_webp/abc/mqdefault_6s.webp'

    def test_missing(self):
        assert ResponseParser.extract_moving_thumbnail({}) is None


class TestExtractChannelThumbnail:
    def test_valid(self):
        renderer = {
            'channelThumbnailSupportedRenderers': {
                'channelThumbnailWithLinkRenderer': {
                    'thumbnail': {
                        'thumbnails': [
                            {'url': 'https://yt3.ggpht.com/avatar=s68', 'width': 68, 'height': 68}
                        ]
                    }
                }
            }
        }
        assert ResponseParser.extract_channel_thumbnail(renderer) == 'https://yt3.ggpht.com/avatar=s68'

    def test_missing(self):
        assert ResponseParser.extract_channel_thumbnail({}) is None


class TestExtractDescriptionSnippet:
    def test_search_format(self):
        renderer = {
            'detailedMetadataSnippets': [{
                'snippetText': {'runs': [{'text': 'This is a description snippet'}]},
                'snippetHoverText': {'runs': [{'text': 'From the video description'}]},
            }]
        }
        assert ResponseParser.extract_description_snippet(renderer) == 'This is a description snippet'

    def test_browse_format(self):
        renderer = {
            'descriptionSnippet': {
                'runs': [{'text': 'Channel video description'}]
            }
        }
        assert ResponseParser.extract_description_snippet(renderer) == 'Channel video description'

    def test_missing(self):
        assert ResponseParser.extract_description_snippet({}) is None


class TestExtractVerifiedBadge:
    def test_verified(self):
        renderer = {
            'ownerBadges': [{
                'metadataBadgeRenderer': {
                    'icon': {'iconType': 'CHECK_CIRCLE_THICK'},
                    'style': 'BADGE_STYLE_TYPE_VERIFIED',
                    'tooltip': 'Verified',
                }
            }]
        }
        assert ResponseParser.extract_verified_badge(renderer) is True

    def test_not_verified(self):
        assert ResponseParser.extract_verified_badge({}) is False

    def test_other_badge_style(self):
        renderer = {
            'ownerBadges': [{
                'metadataBadgeRenderer': {
                    'style': 'BADGE_STYLE_TYPE_SIMPLE',
                }
            }]
        }
        assert ResponseParser.extract_verified_badge(renderer) is False


class TestExtractBadges:
    def test_multiple_badges(self):
        renderer = {
            'badges': [
                {'metadataBadgeRenderer': {'label': 'New'}},
                {'metadataBadgeRenderer': {'label': '4K'}},
            ]
        }
        assert ResponseParser.extract_badges(renderer) == ['New', '4K']

    def test_no_badges(self):
        assert ResponseParser.extract_badges({}) == []


class TestExtractVideoRenderer:
    def test_valid_renderer(self):
        renderer = {
            'videoId': 'abc123',
            'title': {'simpleText': 'Test Video'},
            'ownerText': {'simpleText': 'Test Channel'},
            'lengthText': {'simpleText': '10:30'},
            'publishedTimeText': {'simpleText': '2 days ago'},
        }
        video = ResponseParser.extract_video_renderer(renderer)
        assert video is not None
        assert video.video_id == 'abc123'
        assert video.title == 'Test Video'
        assert video.channel == 'Test Channel'
        assert video.duration == '10:30'
        assert video.duration_seconds == 630
        assert video.published_text == '2 days ago'

    def test_no_video_id(self):
        assert ResponseParser.extract_video_renderer({}) is None

    def test_rich_renderer(self):
        """Test extraction of all new fields from a fully-populated renderer."""
        renderer = {
            'videoId': 'xyz789',
            'title': {'simpleText': 'Rich Video'},
            'ownerText': {'simpleText': 'Rich Channel'},
            'lengthText': {'simpleText': '15:29'},
            'publishedTimeText': {'simpleText': '1 hour ago'},
            'viewCountText': {'simpleText': '17,606 views'},
            'shortViewCountText': {'simpleText': '17K views'},
            'thumbnail': {
                'thumbnails': [
                    {'url': 'https://i.ytimg.com/vi/xyz789/hq720.jpg', 'width': 720, 'height': 404},
                ]
            },
            'richThumbnail': {
                'movingThumbnailRenderer': {
                    'movingThumbnailDetails': {
                        'thumbnails': [{'url': 'https://i.ytimg.com/an_webp/xyz789/mqdefault_6s.webp', 'width': 320, 'height': 180}],
                    }
                }
            },
            'channelThumbnailSupportedRenderers': {
                'channelThumbnailWithLinkRenderer': {
                    'thumbnail': {
                        'thumbnails': [{'url': 'https://yt3.ggpht.com/avatar', 'width': 68, 'height': 68}]
                    }
                }
            },
            'detailedMetadataSnippets': [{
                'snippetText': {'runs': [{'text': 'A description snippet'}]},
            }],
            'ownerBadges': [{
                'metadataBadgeRenderer': {'style': 'BADGE_STYLE_TYPE_VERIFIED'},
            }],
            'badges': [
                {'metadataBadgeRenderer': {'label': 'New'}},
                {'metadataBadgeRenderer': {'label': '4K'}},
            ],
        }
        video = ResponseParser.extract_video_renderer(renderer)
        assert video is not None
        assert video.video_id == 'xyz789'
        assert video.view_count == '17,606 views'
        assert video.short_view_count == '17K views'
        assert len(video.thumbnails) == 1
        assert video.thumbnails[0].width == 720
        assert video.thumbnail_url == 'https://i.ytimg.com/vi/xyz789/hq720.jpg'
        assert video.moving_thumbnail == 'https://i.ytimg.com/an_webp/xyz789/mqdefault_6s.webp'
        assert video.channel_thumbnail == 'https://yt3.ggpht.com/avatar'
        assert video.description_snippet == 'A description snippet'
        assert video.is_verified is True
        assert video.badges == ['New', '4K']


class TestParseTranscriptXml:
    def test_valid_xml(self):
        xml = '''<transcript>
            <text start="0.0" dur="5.0">Hello world</text>
            <text start="5.0" dur="3.5">Second line</text>
        </transcript>'''
        segments = ResponseParser.parse_transcript_xml(xml)
        assert len(segments) == 2
        assert segments[0].text == 'Hello world'
        assert segments[0].start == 0.0
        assert segments[0].duration == 5.0
        assert segments[1].text == 'Second line'

    def test_html_entities(self):
        xml = '<transcript><text start="0" dur="1">Hello &amp; world</text></transcript>'
        segments = ResponseParser.parse_transcript_xml(xml)
        assert segments[0].text == 'Hello & world'

    def test_invalid_xml(self):
        segments = ResponseParser.parse_transcript_xml('not xml')
        assert segments == []

    def test_empty_transcript(self):
        xml = '<transcript></transcript>'
        segments = ResponseParser.parse_transcript_xml(xml)
        assert segments == []

    def test_timedtext_v3_format(self):
        xml = '''<?xml version="1.0" encoding="utf-8" ?><timedtext format="3">
<body>
<p t="0" d="5000">Hello world</p>
<p t="5000" d="3500">Second line</p>
</body>
</timedtext>'''
        segments = ResponseParser.parse_transcript_xml(xml)
        assert len(segments) == 2
        assert segments[0].text == 'Hello world'
        assert segments[0].start == 0.0
        assert segments[0].duration == 5.0
        assert segments[1].text == 'Second line'
        assert segments[1].start == 5.0
        assert segments[1].duration == 3.5

    def test_timedtext_v3_empty_body(self):
        xml = '<timedtext format="3"><body></body></timedtext>'
        segments = ResponseParser.parse_transcript_xml(xml)
        assert segments == []

    def test_timedtext_v3_no_body(self):
        xml = '<timedtext format="3"></timedtext>'
        segments = ResponseParser.parse_transcript_xml(xml)
        assert segments == []


class TestParseSearchResponse:
    def test_valid_response(self):
        data = {
            'contents': {
                'twoColumnSearchResultsRenderer': {
                    'primaryContents': {
                        'sectionListRenderer': {
                            'contents': [{
                                'itemSectionRenderer': {
                                    'contents': [{
                                        'videoRenderer': {
                                            'videoId': 'abc123',
                                            'title': {'simpleText': 'Test'},
                                            'ownerText': {'simpleText': 'Channel'},
                                            'lengthText': {'simpleText': '5:00'},
                                            'publishedTimeText': {'simpleText': '1 day ago'},
                                        }
                                    }]
                                }
                            }]
                        }
                    }
                }
            }
        }
        result, continuation = ResponseParser.parse_search_response(data, 'test query', 20)
        assert result.query == 'test query'
        assert len(result.videos) == 1
        assert result.videos[0].video_id == 'abc123'

    def test_empty_response(self):
        result, continuation = ResponseParser.parse_search_response({}, 'test', 20)
        assert result.videos == []
