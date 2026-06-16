from __future__ import annotations

from html import unescape
from xml.etree import ElementTree

from tubescrape.models import (
    ChannelPlaylistEntry,
    ChannelPlaylistsResult,
    PlaylistEntry,
    PlaylistResult,
    SearchResult,
    ShortResult,
    ShortsResult,
    Thumbnail,
    TranscriptListEntry,
    TranscriptSegment,
    VideoResult,
)


class ResponseParser:
    """Static methods to extract data from InnerTube JSON responses.

    All methods are pure functions with no instance state.
    """

    @staticmethod
    def get_text(obj: dict | None) -> str:
        """Extract text from YouTube's text object format.

        YouTube returns text in two formats:
            {'simpleText': 'some text'}
            {'runs': [{'text': 'some'}, {'text': ' text'}]}
        """
        if not obj:
            return ''
        if 'simpleText' in obj:
            return obj['simpleText']
        if 'runs' in obj:
            return ''.join(run.get('text', '') for run in obj['runs'])
        return ''

    @staticmethod
    def extract_channel_id(renderer: dict) -> str | None:
        """Extract channel ID from a videoRenderer's ownerText browse endpoint."""
        try:
            runs = renderer['ownerText']['runs']
            if runs:
                browse_ep = runs[0]['navigationEndpoint']['browseEndpoint']
                return browse_ep['browseId']
        except (KeyError, TypeError, IndexError):
            pass
        return None

    @staticmethod
    def extract_time_status_style(renderer: dict) -> str:
        """Detect LIVE / SHORTS / DEFAULT from thumbnailOverlays.

        Returns the style string (e.g. 'LIVE', 'SHORTS', 'DEFAULT') or
        empty string if not found.
        """
        for overlay in renderer.get('thumbnailOverlays', []):
            status = overlay.get('thumbnailOverlayTimeStatusRenderer')
            if status:
                return status.get('style', '')
        return ''

    @staticmethod
    def parse_duration(duration_text: str) -> int:
        """Parse duration string like '1:23:45' or '23:45' to seconds.

        Returns 0 if the string cannot be parsed.
        """
        if not duration_text:
            return 0
        str_parts = duration_text.strip().split(':')
        try:
            int_parts = [int(p) for p in str_parts]
        except ValueError:
            return 0
        if len(int_parts) == 3:
            return int_parts[0] * 3600 + int_parts[1] * 60 + int_parts[2]
        if len(int_parts) == 2:
            return int_parts[0] * 60 + int_parts[1]
        return 0

    @staticmethod
    def extract_thumbnails(renderer: dict) -> list[Thumbnail]:
        """Extract thumbnail list from a renderer's thumbnail object."""
        thumb_obj = renderer.get('thumbnail', {})
        thumbnails: list[Thumbnail] = []
        for t in thumb_obj.get('thumbnails', []):
            url = t.get('url', '')
            if url:
                thumbnails.append(Thumbnail(
                    url=url,
                    width=t.get('width', 0),
                    height=t.get('height', 0),
                ))
        return thumbnails

    @staticmethod
    def extract_moving_thumbnail(renderer: dict) -> str | None:
        """Extract animated thumbnail URL from richThumbnail."""
        rich = renderer.get('richThumbnail', {})
        moving = rich.get('movingThumbnailRenderer', {})
        details = moving.get('movingThumbnailDetails', {})
        thumbs = details.get('thumbnails', [])
        if thumbs:
            return thumbs[0].get('url')
        return None

    @staticmethod
    def extract_channel_thumbnail(renderer: dict) -> str | None:
        """Extract channel avatar URL from channelThumbnailSupportedRenderers."""
        supported = renderer.get('channelThumbnailSupportedRenderers', {})
        with_link = supported.get('channelThumbnailWithLinkRenderer', {})
        thumb = with_link.get('thumbnail', {})
        thumbs = thumb.get('thumbnails', [])
        if thumbs:
            return thumbs[0].get('url')
        return None

    @staticmethod
    def extract_description_snippet(renderer: dict) -> str | None:
        """Extract description snippet from videoRenderer.

        Search results use detailedMetadataSnippets, browse results
        use descriptionSnippet.
        """
        # Search results format
        snippets = renderer.get('detailedMetadataSnippets', [])
        if snippets:
            snippet_text = snippets[0].get('snippetText', {})
            text = ResponseParser.get_text(snippet_text)
            if text:
                return text

        # Browse results format
        desc_snippet = renderer.get('descriptionSnippet')
        if desc_snippet:
            text = ResponseParser.get_text(desc_snippet)
            if text:
                return text

        return None

    @staticmethod
    def extract_verified_badge(renderer: dict) -> bool:
        """Check if the channel has a verified badge."""
        for badge in renderer.get('ownerBadges', []):
            badge_renderer = badge.get('metadataBadgeRenderer', {})
            if badge_renderer.get('style') == 'BADGE_STYLE_TYPE_VERIFIED':
                return True
        return False

    @staticmethod
    def extract_badges(renderer: dict) -> list[str]:
        """Extract video badges like 'New', '4K', 'HD', etc."""
        labels: list[str] = []
        for badge in renderer.get('badges', []):
            badge_renderer = badge.get('metadataBadgeRenderer', {})
            label = badge_renderer.get('label', '')
            if label:
                labels.append(label)
        return labels

    @staticmethod
    def extract_video_renderer(renderer: dict) -> VideoResult | None:
        """Parse a single videoRenderer dict into a VideoResult."""
        video_id = renderer.get('videoId', '')
        if not video_id:
            return None

        title = ResponseParser.get_text(renderer.get('title'))
        channel = ResponseParser.get_text(renderer.get('ownerText'))
        duration_text = ResponseParser.get_text(renderer.get('lengthText'))
        published_text = ResponseParser.get_text(renderer.get('publishedTimeText'))
        channel_id = ResponseParser.extract_channel_id(renderer)
        time_status = ResponseParser.extract_time_status_style(renderer)

        # View count
        view_count_text = ResponseParser.get_text(renderer.get('viewCountText'))
        short_view_text = ResponseParser.get_text(renderer.get('shortViewCountText'))

        # Rich media
        thumbnails = ResponseParser.extract_thumbnails(renderer)
        moving_thumbnail = ResponseParser.extract_moving_thumbnail(renderer)
        channel_thumbnail = ResponseParser.extract_channel_thumbnail(renderer)
        description_snippet = ResponseParser.extract_description_snippet(renderer)

        # Badges
        is_verified = ResponseParser.extract_verified_badge(renderer)
        badges = ResponseParser.extract_badges(renderer)

        return VideoResult(
            video_id=video_id,
            title=title,
            channel=channel,
            channel_id=channel_id,
            duration=duration_text or None,
            duration_seconds=ResponseParser.parse_duration(duration_text),
            published_text=published_text or None,
            url=f'https://www.youtube.com/watch?v={video_id}',
            is_live=time_status == 'LIVE',
            is_short=time_status == 'SHORTS',
            view_count=view_count_text or None,
            short_view_count=short_view_text or None,
            thumbnails=thumbnails,
            moving_thumbnail=moving_thumbnail,
            channel_thumbnail=channel_thumbnail,
            description_snippet=description_snippet,
            is_verified=is_verified,
            badges=badges,
        )

    @staticmethod
    def parse_search_response(data: dict, query: str, max_results: int) -> SearchResult:
        """Parse the full search API response into a SearchResult."""
        videos: list[VideoResult] = []

        try:
            sections = (
                data['contents']['twoColumnSearchResultsRenderer']
                ['primaryContents']['sectionListRenderer']['contents']
            )
        except (KeyError, TypeError):
            return SearchResult(query=query, videos=[])

        for section in sections:
            items = section.get('itemSectionRenderer', {}).get('contents', [])
            for item in items:
                renderer = item.get('videoRenderer')
                if not renderer:
                    continue

                video = ResponseParser.extract_video_renderer(renderer)
                if video:
                    videos.append(video)

                if len(videos) >= max_results:
                    return SearchResult(query=query, videos=videos)

        return SearchResult(query=query, videos=videos)

    @staticmethod
    def parse_browse_first_page(
        data: dict, channel_id: str,
    ) -> tuple[list[VideoResult], str | None]:
        """Parse the first browse response.

        Returns (videos, continuation_token).
        """
        try:
            tabs = data['contents']['twoColumnBrowseResultsRenderer']['tabs']
        except (KeyError, TypeError):
            return [], None

        for tab in tabs:
            tab_renderer = tab.get('tabRenderer', {})
            content = tab_renderer.get('content', {})
            rich_grid = content.get('richGridRenderer', {})
            if rich_grid.get('contents'):
                return ResponseParser._extract_videos_and_continuation(
                    rich_grid['contents']
                )

        return [], None

    @staticmethod
    def parse_browse_continuation(data: dict) -> tuple[list[VideoResult], str | None]:
        """Parse a continuation browse response.

        Returns (videos, continuation_token).
        """
        try:
            actions = data['onResponseReceivedActions']
        except (KeyError, TypeError):
            return [], None

        for action in actions:
            items = (
                action.get('appendContinuationItemsAction', {})
                .get('continuationItems', [])
            )
            if items:
                return ResponseParser._extract_videos_and_continuation(items)

        return [], None

    @staticmethod
    def _extract_videos_and_continuation(
        items: list,
    ) -> tuple[list[VideoResult], str | None]:
        """Extract VideoResult objects and continuation token from grid items."""
        videos: list[VideoResult] = []
        continuation: str | None = None

        for item in items:
            # Video items
            rich_item = item.get('richItemRenderer', {})
            content = rich_item.get('content', {})

            # Legacy format: videoRenderer
            renderer = content.get('videoRenderer')
            if renderer:
                video = ResponseParser.extract_video_renderer(renderer)
                if video:
                    videos.append(video)
                continue

            # New format: lockupViewModel (YouTube 2025+ change)
            lockup = content.get('lockupViewModel')
            if lockup and lockup.get('contentType') == 'LOCKUP_CONTENT_TYPE_VIDEO':
                video = ResponseParser._parse_video_lockup(lockup)
                if video:
                    videos.append(video)
                continue

            # Continuation token (legacy)
            cont_item = item.get('continuationItemRenderer', {})
            cont_endpoint = cont_item.get('continuationEndpoint', {})
            cont_command = cont_endpoint.get('continuationCommand', {})
            token = cont_command.get('token')
            if token:
                continuation = token

        return videos, continuation

    @staticmethod
    def parse_player_captions(data: dict) -> tuple[list[dict], list[dict]]:
        """Extract caption tracks and translation languages from player response.

        Returns (caption_tracks, translation_languages).
        """
        captions = data.get('captions')
        if captions is None or 'playerCaptionsTracklistRenderer' not in captions:
            return [], []

        renderer = captions['playerCaptionsTracklistRenderer']
        caption_tracks = renderer.get('captionTracks', [])
        translation_languages = renderer.get('translationLanguages', [])
        return caption_tracks, translation_languages

    @staticmethod
    def parse_caption_tracks(caption_tracks: list[dict]) -> list[TranscriptListEntry]:
        """Convert raw caption track dicts into TranscriptListEntry objects."""
        entries: list[TranscriptListEntry] = []
        for track in caption_tracks:
            lang_code = track.get('languageCode', '')
            name = track.get('name', {})
            language = ResponseParser.get_text(name) if isinstance(name, dict) else str(name)
            is_auto = track.get('kind', '') == 'asr'

            entries.append(TranscriptListEntry(
                language=language,
                language_code=lang_code,
                is_generated=is_auto,
                is_translatable=track.get('isTranslatable', False),
                base_url=track.get('baseUrl', ''),
            ))
        return entries

    @staticmethod
    def parse_transcript_xml(xml_text: str) -> list[TranscriptSegment]:
        """Parse YouTube transcript XML into a list of TranscriptSegment.

        Supports two formats:

        Format 1 (legacy):
            <transcript>
                <text start="0.0" dur="5.0">Hello world</text>
            </transcript>

        Format 2 (timedtext v3):
            <timedtext format="3">
                <body>
                    <p t="0" d="5000">Hello world</p>
                </body>
            </timedtext>
        """
        try:
            root = ElementTree.fromstring(xml_text)
        except ElementTree.ParseError:
            return []

        # Detect format by root tag
        if root.tag == 'timedtext':
            return ResponseParser._parse_timedtext_v3(root)

        return ResponseParser._parse_transcript_legacy(root)

    @staticmethod
    def _parse_transcript_legacy(root: ElementTree.Element) -> list[TranscriptSegment]:
        """Parse legacy <transcript><text> format."""
        segments: list[TranscriptSegment] = []
        for element in root:
            raw = ''.join(element.itertext())
            if not raw:
                continue

            text = unescape(raw).strip()
            if not text:
                continue

            start = float(element.get('start', 0))
            duration = float(element.get('dur', 0))
            segments.append(TranscriptSegment(
                text=text,
                start=start,
                duration=duration,
            ))

        return segments

    @staticmethod
    def _parse_timedtext_v3(root: ElementTree.Element) -> list[TranscriptSegment]:
        """Parse timedtext format 3: <timedtext><body><p t="ms" d="ms">."""
        segments: list[TranscriptSegment] = []

        body = root.find('body')
        if body is None:
            return segments

        for element in body:
            if element.tag != 'p':
                continue

            raw = ''.join(element.itertext())
            if not raw:
                continue

            text = unescape(raw).strip()
            if not text:
                continue

            # t and d are in milliseconds
            start_ms = int(element.get('t', 0))
            duration_ms = int(element.get('d', 0))
            segments.append(TranscriptSegment(
                text=text,
                start=start_ms / 1000.0,
                duration=duration_ms / 1000.0,
            ))

        return segments

    @staticmethod
    def extract_playability_status(data: dict) -> dict:
        """Extract playability status from player response."""
        return data.get('playabilityStatus', {})

    @staticmethod
    def parse_playlist_response(
        data: dict, playlist_id: str,
    ) -> tuple[PlaylistResult, str | None]:
        """Parse a playlist browse response.

        Returns (PlaylistResult, continuation_token).
        """
        title: str | None = None
        channel: str | None = None
        videos: list[PlaylistEntry] = []
        continuation: str | None = None

        # Extract playlist metadata from header
        header = data.get('header', {})
        playlist_header = header.get('playlistHeaderRenderer', {})
        if playlist_header:
            title = ResponseParser.get_text(playlist_header.get('title'))
            owner = playlist_header.get('ownerText', {})
            channel = ResponseParser.get_text(owner)

        # pageHeaderRenderer (current format)
        page_header = header.get('pageHeaderRenderer', {})
        ph_content = page_header.get('content', {}).get('pageHeaderViewModel', {})
        if not title:
            title = (
                ph_content.get('title', {})
                .get('dynamicTextViewModel', {})
                .get('text', {})
                .get('content', '')
            )
        if not channel:
            ph_meta = ph_content.get('metadata', {}).get('contentMetadataViewModel', {})
            for row in ph_meta.get('metadataRows', []):
                for part in row.get('metadataParts', []):
                    avatar = part.get('avatarStack', {}).get('avatarStackViewModel', {})
                    text = avatar.get('text', {}).get('content', '')
                    if text:
                        if text.startswith('by '):
                            channel = text.removeprefix('by ').strip()
                        else:
                            channel = text

        # Fallback: metadata.playlistMetadataRenderer
        if not title:
            meta_renderer = data.get('metadata', {}).get('playlistMetadataRenderer', {})
            if meta_renderer:
                title = meta_renderer.get('title')

        # Extract videos from contents
        try:
            tabs = data['contents']['twoColumnBrowseResultsRenderer']['tabs']
        except (KeyError, TypeError):
            return PlaylistResult(
                playlist_id=playlist_id, title=title, channel=channel,
            ), None

        for tab in tabs:
            tab_content = tab.get('tabRenderer', {}).get('content', {})
            section_list = tab_content.get('sectionListRenderer', {})
            for section in section_list.get('contents', []):
                # New format: continuationItemViewModel at section level
                token = ResponseParser._extract_continuation_token_vm(section)
                if token:
                    continuation = token
                    continue

                item_section = section.get('itemSectionRenderer', {})
                for item in item_section.get('contents', []):
                    # New format: lockupViewModel directly in itemSection
                    lockup = item.get('lockupViewModel')
                    if lockup and lockup.get('contentType') == 'LOCKUP_CONTENT_TYPE_VIDEO':
                        entry = ResponseParser._parse_playlist_video_lockup(lockup)
                        if entry:
                            videos.append(entry)
                        continue

                    # Legacy format: playlistVideoListRenderer
                    playlist_renderer = item.get('playlistVideoListRenderer', {})
                    for content in playlist_renderer.get('contents', []):
                        video = content.get('playlistVideoRenderer')
                        if video:
                            entry = ResponseParser._parse_playlist_video(video)
                            if entry:
                                videos.append(entry)
                            continue

                        # Continuation token (legacy)
                        cont = content.get('continuationItemRenderer', {})
                        cont_ep = cont.get('continuationEndpoint', {})
                        cont_cmd = cont_ep.get('continuationCommand', {})
                        token = cont_cmd.get('token')
                        if token:
                            continuation = token

        return PlaylistResult(
            playlist_id=playlist_id,
            title=title,
            channel=channel,
            videos=videos,
        ), continuation

    @staticmethod
    def parse_playlist_continuation(
        data: dict,
    ) -> tuple[list[PlaylistEntry], str | None]:
        """Parse a playlist continuation response."""
        videos: list[PlaylistEntry] = []
        continuation: str | None = None

        try:
            actions = data['onResponseReceivedActions']
        except (KeyError, TypeError):
            return [], None

        for action in actions:
            items = (
                action.get('appendContinuationItemsAction', {})
                .get('continuationItems', [])
            )
            for item in items:
                # Legacy format
                video = item.get('playlistVideoRenderer')
                if video:
                    entry = ResponseParser._parse_playlist_video(video)
                    if entry:
                        videos.append(entry)
                    continue

                # New format: lockupViewModel inside itemSectionRenderer
                isr = item.get('itemSectionRenderer', {})
                for content in isr.get('contents', []):
                    lockup = content.get('lockupViewModel')
                    if lockup and lockup.get('contentType') == 'LOCKUP_CONTENT_TYPE_VIDEO':
                        entry = ResponseParser._parse_playlist_video_lockup(lockup)
                        if entry:
                            videos.append(entry)

                # New continuation format
                token = ResponseParser._extract_continuation_token_vm(item)
                if token:
                    continuation = token
                    continue

                # Legacy continuation format
                cont = item.get('continuationItemRenderer', {})
                cont_ep = cont.get('continuationEndpoint', {})
                cont_cmd = cont_ep.get('continuationCommand', {})
                token = cont_cmd.get('token')
                if token:
                    continuation = token

        return videos, continuation

    # ── Shorts Tab ──

    @staticmethod
    def parse_shorts_tab(data: dict, channel_id: str) -> ShortsResult:
        """Parse a channel's Shorts tab response."""
        shorts: list[ShortResult] = []

        try:
            tabs = data['contents']['twoColumnBrowseResultsRenderer']['tabs']
        except (KeyError, TypeError):
            return ShortsResult(channel_id=channel_id)

        for tab in tabs:
            tr = tab.get('tabRenderer', {})
            if not tr.get('selected'):
                continue
            content = tr.get('content', {})
            rich_grid = content.get('richGridRenderer', {})
            for item in rich_grid.get('contents', []):
                ri = item.get('richItemRenderer', {}).get('content', {})
                lockup = ri.get('shortsLockupViewModel', {})
                if not lockup:
                    continue

                short = ResponseParser._parse_short_lockup(lockup)
                if short:
                    shorts.append(short)

        return ShortsResult(channel_id=channel_id, shorts=shorts)

    @staticmethod
    def _parse_short_lockup(lockup: dict) -> ShortResult | None:
        """Parse a shortsLockupViewModel into a ShortResult."""
        on_tap = lockup.get('onTap', {}).get('innertubeCommand', {})
        reel_ep = on_tap.get('reelWatchEndpoint', {})
        video_id = reel_ep.get('videoId', '')
        if not video_id:
            return None

        overlay = lockup.get('overlayMetadata', {})
        title = overlay.get('primaryText', {}).get('content', '')
        view_count = overlay.get('secondaryText', {}).get('content', '')

        thumb_vm = lockup.get('thumbnailViewModel', {}).get('thumbnailViewModel', {})
        sources = thumb_vm.get('image', {}).get('sources', [])
        thumbnail_url = sources[0].get('url') if sources else None

        return ShortResult(
            video_id=video_id,
            title=title,
            view_count=view_count or None,
            thumbnail_url=thumbnail_url,
        )

    # ── Channel Playlists Tab ──

    @staticmethod
    def parse_channel_playlists_tab(
        data: dict, channel_id: str,
    ) -> ChannelPlaylistsResult:
        """Parse a channel's Playlists tab response."""
        playlists: list[ChannelPlaylistEntry] = []

        try:
            tabs = data['contents']['twoColumnBrowseResultsRenderer']['tabs']
        except (KeyError, TypeError):
            return ChannelPlaylistsResult(channel_id=channel_id)

        for tab in tabs:
            tr = tab.get('tabRenderer', {})
            if not tr.get('selected'):
                continue
            content = tr.get('content', {})

            # Playlists tab uses sectionListRenderer > itemSectionRenderer > gridRenderer
            section_list = content.get('sectionListRenderer', {}).get('contents', [])
            for section in section_list:
                items = section.get('itemSectionRenderer', {}).get('contents', [])
                for item in items:
                    grid = item.get('gridRenderer', {})
                    for grid_item in grid.get('items', []):
                        entry = ResponseParser._parse_channel_playlist_item(grid_item)
                        if entry:
                            playlists.append(entry)

        return ChannelPlaylistsResult(channel_id=channel_id, playlists=playlists)

    @staticmethod
    def _parse_channel_playlist_item(item: dict) -> ChannelPlaylistEntry | None:
        """Parse a lockupViewModel or gridPlaylistRenderer into a ChannelPlaylistEntry."""
        # New ViewModel format
        lockup = item.get('lockupViewModel')
        if lockup:
            playlist_id = lockup.get('contentId', '')
            if not playlist_id:
                return None

            title = ''
            video_count = None
            metadata = lockup.get('metadata', {}).get('lockupMetadataViewModel', {})
            if metadata:
                title = metadata.get('title', {}).get('content', '')
                # Extract video count from metadata rows
                meta_container = metadata.get('metadata', {})
                if 'contentMetadataViewModel' in meta_container:
                    rows = meta_container['contentMetadataViewModel'].get('metadataRows', [])
                    for row in rows:
                        for part in row.get('metadataParts', []):
                            text = part.get('text', {}).get('content', '')
                            if 'video' in text.lower():
                                video_count = text

            # Thumbnail and video count from badge
            thumbnail_url = None
            content_image = lockup.get('contentImage', {})
            coll = content_image.get('collectionThumbnailViewModel', {})
            primary = coll.get('primaryThumbnail', {}).get('thumbnailViewModel', {})
            sources = primary.get('image', {}).get('sources', [])
            if sources:
                thumbnail_url = sources[0].get('url')

            # Video count from thumbnail overlay badge (e.g. "10 videos" or "37 lessons")
            if video_count is None:
                for overlay in primary.get('overlays', []):
                    badge_vm = overlay.get('thumbnailOverlayBadgeViewModel', {})
                    for badge in badge_vm.get('thumbnailBadges', []):
                        text = badge.get('thumbnailBadgeViewModel', {}).get('text', '')
                        if text:
                            video_count = text

            return ChannelPlaylistEntry(
                playlist_id=playlist_id,
                title=title,
                thumbnail_url=thumbnail_url,
                video_count=video_count,
            )

        # Legacy gridPlaylistRenderer format
        gpr = item.get('gridPlaylistRenderer')
        if gpr:
            playlist_id = gpr.get('playlistId', '')
            if not playlist_id:
                return None

            title = ResponseParser.get_text(gpr.get('title'))
            video_count_text = ResponseParser.get_text(gpr.get('videoCountShortText'))
            thumbnails = gpr.get('thumbnail', {}).get('thumbnails', [])
            thumbnail_url = thumbnails[-1].get('url') if thumbnails else None

            return ChannelPlaylistEntry(
                playlist_id=playlist_id,
                title=title,
                thumbnail_url=thumbnail_url,
                video_count=video_count_text or None,
            )

        return None

    # ── Channel Search ──

    @staticmethod
    def parse_channel_search(data: dict, channel_id: str, query: str) -> SearchResult:
        """Parse a channel search response (expandableTabRenderer)."""
        videos: list[VideoResult] = []

        try:
            tabs = data['contents']['twoColumnBrowseResultsRenderer']['tabs']
        except (KeyError, TypeError):
            return SearchResult(query=query)

        for tab in tabs:
            expandable = tab.get('expandableTabRenderer', {})
            if not expandable.get('selected'):
                continue
            content = expandable.get('content', {})
            section_list = content.get('sectionListRenderer', {}).get('contents', [])
            for section in section_list:
                items = section.get('itemSectionRenderer', {}).get('contents', [])
                for item in items:
                    renderer = item.get('videoRenderer')
                    if renderer:
                        video = ResponseParser.extract_video_renderer(renderer)
                        if video:
                            videos.append(video)

        return SearchResult(query=query, videos=videos)

    @staticmethod
    def _parse_video_lockup(lockup: dict) -> VideoResult | None:
        """Parse a lockupViewModel (new format) into a VideoResult."""
        video_id = lockup.get('contentId', '')
        if not video_id:
            return None

        metadata = lockup.get('metadata', {}).get('lockupMetadataViewModel', {})
        title = metadata.get('title', {}).get('content', '')

        # Extract metadata rows (view count, published date)
        view_count = None
        published_text = None
        meta_container = metadata.get('metadata', {}).get('contentMetadataViewModel', {})
        for row in meta_container.get('metadataRows', []):
            for part in row.get('metadataParts', []):
                text = part.get('text', {}).get('content', '')
                if not text:
                    continue
                if 'view' in text.lower() or 'watching' in text.lower():
                    view_count = text
                elif text and not view_count:
                    # Could be channel name or other info
                    pass
                else:
                    published_text = text

        # Re-parse: metadata parts come in pairs per row typically
        # Row 0 often has views + date
        parts_list: list[str] = []
        for row in meta_container.get('metadataRows', []):
            for part in row.get('metadataParts', []):
                text = part.get('text', {}).get('content', '')
                if text:
                    parts_list.append(text)

        view_count = None
        published_text = None
        for text in parts_list:
            if 'view' in text.lower() or 'watching' in text.lower():
                view_count = text
            elif 'ago' in text.lower() or 'streamed' in text.lower():
                published_text = text

        # Duration from thumbnail badge
        duration_text = ''
        is_live = False
        is_short = False
        thumb_vm = lockup.get('contentImage', {}).get('thumbnailViewModel', {})
        for overlay in thumb_vm.get('overlays', []):
            bottom = overlay.get('thumbnailBottomOverlayViewModel', {})
            for badge in bottom.get('badges', []):
                bvm = badge.get('thumbnailBadgeViewModel', {})
                badge_style = bvm.get('badgeStyle', '')
                badge_text = bvm.get('text', '')
                if badge_style == 'THUMBNAIL_OVERLAY_BADGE_STYLE_LIVE':
                    is_live = True
                elif badge_text:
                    duration_text = badge_text

        # Thumbnails
        sources = thumb_vm.get('image', {}).get('sources', [])
        thumbnails = [
            Thumbnail(url=s.get('url', ''), width=s.get('width', 0), height=s.get('height', 0))
            for s in sources if s.get('url')
        ]

        return VideoResult(
            video_id=video_id,
            title=title,
            channel='',
            channel_id=None,
            duration=duration_text or None,
            duration_seconds=ResponseParser.parse_duration(duration_text),
            published_text=published_text,
            url=f'https://www.youtube.com/watch?v={video_id}',
            is_live=is_live,
            is_short=is_short,
            view_count=view_count,
            short_view_count=None,
            thumbnails=thumbnails,
            moving_thumbnail=None,
            channel_thumbnail=None,
            description_snippet=None,
            is_verified=False,
            badges=[],
        )

    @staticmethod
    def _parse_playlist_video_lockup(lockup: dict) -> PlaylistEntry | None:
        """Parse a lockupViewModel (new format) into a PlaylistEntry."""
        video_id = lockup.get('contentId', '')
        if not video_id:
            return None

        metadata = lockup.get('metadata', {}).get('lockupMetadataViewModel', {})
        title = metadata.get('title', {}).get('content', '')

        # Extract channel name from metadata rows
        channel = ''
        meta_container = metadata.get('metadata', {}).get('contentMetadataViewModel', {})
        for row in meta_container.get('metadataRows', []):
            for part in row.get('metadataParts', []):
                text = part.get('text', {}).get('content', '')
                lower = text.lower()
                if text and not channel and 'view' not in lower and 'ago' not in lower:
                    channel = text

        # Duration from thumbnail badge
        duration_text = ''
        thumb_vm = lockup.get('contentImage', {}).get('thumbnailViewModel', {})
        for overlay in thumb_vm.get('overlays', []):
            bottom = overlay.get('thumbnailBottomOverlayViewModel', {})
            for badge in bottom.get('badges', []):
                bvm = badge.get('thumbnailBadgeViewModel', {})
                text = bvm.get('text', '')
                if text:
                    duration_text = text

        # Thumbnails
        sources = thumb_vm.get('image', {}).get('sources', [])
        thumbnails = [
            Thumbnail(url=s.get('url', ''), width=s.get('width', 0), height=s.get('height', 0))
            for s in sources if s.get('url')
        ]

        return PlaylistEntry(
            video_id=video_id,
            title=title,
            channel=channel,
            duration=duration_text or None,
            duration_seconds=ResponseParser.parse_duration(duration_text),
            position=0,
            url=f'https://www.youtube.com/watch?v={video_id}',
            thumbnails=thumbnails,
        )

    @staticmethod
    def _extract_continuation_token_vm(item: dict) -> str | None:
        """Extract continuation token from a continuationItemViewModel."""
        civm = item.get('continuationItemViewModel', {})
        inner = civm.get('continuationCommand', {}).get('innertubeCommand', {})
        return inner.get('continuationCommand', {}).get('token')

    @staticmethod
    def _parse_playlist_video(renderer: dict) -> PlaylistEntry | None:
        """Parse a single playlistVideoRenderer into a PlaylistEntry."""
        video_id = renderer.get('videoId', '')
        if not video_id:
            return None

        title = ResponseParser.get_text(renderer.get('title'))
        channel = ResponseParser.get_text(renderer.get('shortBylineText'))
        duration_text = ResponseParser.get_text(renderer.get('lengthText'))
        index_text = ResponseParser.get_text(renderer.get('index'))
        thumbnails = ResponseParser.extract_thumbnails(renderer)

        try:
            position = int(index_text) if index_text else 0
        except ValueError:
            position = 0

        return PlaylistEntry(
            video_id=video_id,
            title=title,
            channel=channel,
            duration=duration_text or None,
            duration_seconds=ResponseParser.parse_duration(duration_text),
            position=position,
            url=f'https://www.youtube.com/watch?v={video_id}',
            thumbnails=thumbnails,
        )
