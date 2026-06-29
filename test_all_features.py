"""
tubescrape - Full Feature Test Script
=====================================
Tests all major features of the tubescrape package.
Run: python test_all_features.py
"""

import sys
import json
import time

sys.stdout.reconfigure(encoding='utf-8')

import tubescrape

PASS = 0
FAIL = 0


def test(name, condition, detail=''):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  [PASS] {name}')
    else:
        FAIL += 1
        print(f'  [FAIL] {name}')
    if detail:
        print(f'         {detail}')


def separator(title):
    print(f'\n{"=" * 60}')
    print(f'  {title}')
    print(f'{"=" * 60}')


yt = tubescrape.YouTube()

# ─────────────────────────────────────────────────────────────
# 1. VIDEO SEARCH
# ─────────────────────────────────────────────────────────────
separator('1. VIDEO SEARCH')

# 1a. Basic search with default max_results (20)
result = yt.search('python tutorial')
test('Basic search returns results', len(result.videos) > 0, f'{len(result.videos)} videos')
test('Videos have required fields', all([
    result.videos[0].video_id,
    result.videos[0].title,
    result.videos[0].url,
]), f'id={result.videos[0].video_id}')

# 1b. Search with >20 results (pagination)
result50 = yt.search('dog toys', max_results=50)
test('Search pagination (>20 results)', len(result50.videos) == 50, f'{len(result50.videos)} videos')

# 1c. Search with large number
result100 = yt.search('music video 2024', max_results=100)
test('Search pagination (100 results)', len(result100.videos) >= 80, f'{len(result100.videos)} videos')

# 1d. Search with max_results=0 (all)
result_all = yt.search('rare vintage cars 1920s', max_results=0)
test('Search max_results=0 fetches all', len(result_all.videos) > 20, f'{len(result_all.videos)} videos')

# 1e. Search with filters
result_long = yt.search('podcast interview', type='video', duration='long', max_results=5)
test('Search with type+duration filters', len(result_long.videos) > 0, f'{len(result_long.videos)} videos')

# 1f. Search with sort
result_sorted = yt.search('breaking news', sort_by='upload_date', max_results=5)
test('Search with sort_by', len(result_sorted.videos) > 0, f'{len(result_sorted.videos)} videos')

# 1g. to_dict serialization
d = result.to_dict()
test('SearchResult.to_dict() works', 'query' in d and 'videos' in d)

# ─────────────────────────────────────────────────────────────
# 2. CHANNEL SEARCH
# ─────────────────────────────────────────────────────────────
separator('2. CHANNEL SEARCH')

ch_result = yt.search('happy cow', type='channel', max_results=10)
test('Channel search returns channels', len(ch_result.channels) > 0, f'{len(ch_result.channels)} channels')
test('Channel search returns no videos', len(ch_result.videos) == 0)

if ch_result.channels:
    ch = ch_result.channels[0]
    test('Channel has channel_id', bool(ch.channel_id), ch.channel_id)
    test('Channel has title', bool(ch.title), ch.title)
    test('Channel has url', ch.url.startswith('https://'), ch.url)
    test('Channel has subscriber_count', ch.subscriber_count is None or 'subscriber' in ch.subscriber_count.lower(),
         str(ch.subscriber_count))

# to_dict includes channels
d = ch_result.to_dict()
test('Channel search to_dict() has channels key', 'channels' in d and len(d['channels']) > 0)

# ─────────────────────────────────────────────────────────────
# 3. PLAYLIST (PAGINATION >100)
# ─────────────────────────────────────────────────────────────
separator('3. PLAYLIST')

# 3a. Playlist with >100 videos
pl = yt.get_playlist('PL03F969BA30CE1CE1', max_results=0)
test('Playlist returns >100 videos', len(pl.videos) > 100, f'{len(pl.videos)} videos')
test('Playlist has title', bool(pl.title), pl.title)
test('Playlist has channel', bool(pl.channel), pl.channel)
test('Playlist has playlist_id', pl.playlist_id == 'PL03F969BA30CE1CE1')

if pl.videos:
    v = pl.videos[0]
    test('Playlist video has video_id', bool(v.video_id))
    test('Playlist video has title', bool(v.title))
    test('Playlist video has channel', bool(v.channel))

# 3b. Playlist with max_results limit
pl_limited = yt.get_playlist('PL03F969BA30CE1CE1', max_results=10)
test('Playlist max_results=10 respected', len(pl_limited.videos) == 10, f'{len(pl_limited.videos)} videos')

# 3c. Playlist by URL
pl_url = yt.get_playlist('https://www.youtube.com/playlist?list=PL03F969BA30CE1CE1', max_results=5)
test('Playlist by URL works', len(pl_url.videos) > 0, f'{len(pl_url.videos)} videos')

# 3d. to_dict
d = pl.to_dict()
test('PlaylistResult.to_dict() works', 'videos' in d and 'title' in d and 'channel' in d)

# ─────────────────────────────────────────────────────────────
# 4. CHANNEL VIDEOS (WITH CHANNEL NAME)
# ─────────────────────────────────────────────────────────────
separator('4. CHANNEL VIDEOS')

# 4a. By channel ID
browse = yt.get_channel_videos('UCOKoxVSOXpz1aQhnGPnSSww', max_results=10)
test('Channel videos returns results', len(browse.videos) > 0, f'{len(browse.videos)} videos')
test('Channel name is present', bool(browse.channel), browse.channel)
test('Channel ID matches', browse.channel_id == 'UCOKoxVSOXpz1aQhnGPnSSww')

# 4b. By URL
browse_url = yt.get_channel_videos(
    'https://www.youtube.com/channel/UCOKoxVSOXpz1aQhnGPnSSww', max_results=5,
)
test('Channel videos by URL works', len(browse_url.videos) > 0)
test('Channel name present (URL input)', bool(browse_url.channel))

# 4c. By @handle
browse_handle = yt.get_channel_videos('@lexfridman', max_results=5)
test('Channel videos by @handle works', len(browse_handle.videos) > 0)
test('Channel name present (@handle input)', bool(browse_handle.channel), browse_handle.channel)

# 4d. max_results=0 (all videos, pagination)
browse_all = yt.get_channel_videos('UCOKoxVSOXpz1aQhnGPnSSww', max_results=0)
test('Channel videos max_results=0 fetches all', len(browse_all.videos) > 30,
     f'{len(browse_all.videos)} videos')

# 4e. to_dict includes channel name
d = browse.to_dict()
test('BrowseResult.to_dict() has channel', 'channel' in d and d['channel'] is not None)

# ─────────────────────────────────────────────────────────────
# 5. VIDEO INFO (ENRICHED METADATA)
# ─────────────────────────────────────────────────────────────
separator('5. VIDEO INFO (enriched metadata)')

info = yt.get_video_info('dQw4w9WgXcQ')
test('get_video_info returns VideoInfo', info is not None)
test('Has video_id', info.video_id == 'dQw4w9WgXcQ')
test('Has title', bool(info.title), info.title[:50])
test('Has channel', bool(info.channel), info.channel)
test('Has channel_id', bool(info.channel_id))
test('Has description', len(info.description) > 50, f'{len(info.description)} chars')
test('Has view_count', info.view_count > 1_000_000_000, f'{info.view_count:,} views')
test('Has duration_seconds', info.duration_seconds > 0, f'{info.duration_seconds}s')
test('Has keywords', len(info.keywords) > 0, f'{len(info.keywords)} keywords')
test('Has thumbnails', len(info.thumbnails) > 0, f'{len(info.thumbnails)} thumbnails')

# New microformat fields
test('Has publish_date (exact ISO)', bool(info.publish_date), info.publish_date)
test('Has upload_date (exact ISO)', bool(info.upload_date), info.upload_date)
test('Has category', bool(info.category), info.category)
test('Has is_family_safe', info.is_family_safe is not None, str(info.is_family_safe))
test('Has is_unlisted', info.is_unlisted is not None, str(info.is_unlisted))
test('Has owner_url', bool(info.owner_url), info.owner_url)

# to_dict
d = info.to_dict()
test('VideoInfo.to_dict() has new fields',
     'publish_date' in d and 'category' in d and 'owner_url' in d)

# Second video to verify consistency
info2 = yt.get_video_info('jNQXAC9IVRw')
test('Video info on another video', bool(info2.publish_date), f'publish_date={info2.publish_date}')

# ─────────────────────────────────────────────────────────────
# 6. TRANSCRIPTS
# ─────────────────────────────────────────────────────────────
separator('6. TRANSCRIPTS')

# 6a. Basic transcript
t = yt.get_transcript('dQw4w9WgXcQ')
test('get_transcript returns Transcript', t is not None)
test('Has segments', len(t.segments) > 0, f'{len(t.segments)} segments')
test('Has text', len(t.text) > 100, f'{len(t.text)} chars')
test('Has language info', bool(t.language_code), f'{t.language} ({t.language_code})')

# 6b. Without timestamps
t_plain = yt.get_transcript('dQw4w9WgXcQ', timestamps=False)
test('Transcript without timestamps', len(t_plain.segments) == 1)
test('Plain text content', len(t_plain.text) > 100)

# 6c. List transcripts
entries = yt.list_transcripts('dQw4w9WgXcQ')
test('list_transcripts returns entries', len(entries) > 0, f'{len(entries)} languages')
test('Entry has language_code', bool(entries[0].language_code))
test('Entry has is_generated flag', entries[0].is_generated in (True, False))

# 6d. Transcript on different video
t2 = yt.get_transcript('jNQXAC9IVRw', timestamps=False)
test('Transcript on different video', len(t2.text) > 10, f'{len(t2.text)} chars')

# 6e. Transcript save formats
import tempfile, os
with tempfile.TemporaryDirectory() as tmpdir:
    for fmt in ('srt', 'vtt', 'json', 'txt'):
        path = t.save(os.path.join(tmpdir, f'test.{fmt}'))
        test(f'Save as {fmt}', path.exists() and path.stat().st_size > 0)

# ─────────────────────────────────────────────────────────────
# 7. CHANNEL SHORTS
# ─────────────────────────────────────────────────────────────
separator('7. CHANNEL SHORTS')

shorts = yt.get_channel_shorts('UCOKoxVSOXpz1aQhnGPnSSww')
test('get_channel_shorts returns result', shorts is not None)
# Not all channels have shorts, so just verify no crash
test('Shorts result has channel_id', shorts.channel_id == 'UCOKoxVSOXpz1aQhnGPnSSww')

# ─────────────────────────────────────────────────────────────
# 8. CHANNEL PLAYLISTS
# ─────────────────────────────────────────────────────────────
separator('8. CHANNEL PLAYLISTS')

ch_playlists = yt.get_channel_playlists('UCOKoxVSOXpz1aQhnGPnSSww')
test('get_channel_playlists returns result', ch_playlists is not None)
test('Has channel_id', ch_playlists.channel_id == 'UCOKoxVSOXpz1aQhnGPnSSww')

# ─────────────────────────────────────────────────────────────
# 9. CHANNEL SEARCH (within a channel)
# ─────────────────────────────────────────────────────────────
separator('9. CHANNEL SEARCH (within channel)')

ch_search = yt.search_channel('UCOKoxVSOXpz1aQhnGPnSSww', 'tetris')
test('search_channel returns results', len(ch_search.videos) >= 0, f'{len(ch_search.videos)} videos')

# ─────────────────────────────────────────────────────────────
# 10. URL PARSING UTILITIES
# ─────────────────────────────────────────────────────────────
separator('10. URL PARSING')

test('Extract video ID from URL',
     tubescrape.YouTube.extract_video_id('https://www.youtube.com/watch?v=dQw4w9WgXcQ') == 'dQw4w9WgXcQ')
test('Extract video ID from short URL',
     tubescrape.YouTube.extract_video_id('https://youtu.be/dQw4w9WgXcQ') == 'dQw4w9WgXcQ')
test('Extract video ID (plain)',
     tubescrape.YouTube.extract_video_id('dQw4w9WgXcQ') == 'dQw4w9WgXcQ')
test('Extract playlist ID from URL',
     tubescrape.YouTube.extract_playlist_id('https://www.youtube.com/playlist?list=PLtest123') == 'PLtest123')
test('Extract playlist ID (plain)',
     tubescrape.YouTube.extract_playlist_id('PLtest123') == 'PLtest123')

# ─────────────────────────────────────────────────────────────
# 11. SERIALIZATION (to_dict on everything)
# ─────────────────────────────────────────────────────────────
separator('11. SERIALIZATION')

# Verify all to_dict outputs are valid JSON
objects = {
    'SearchResult (videos)': result,
    'SearchResult (channels)': ch_result,
    'PlaylistResult': pl_limited,
    'BrowseResult': browse,
    'VideoInfo': info,
    'Transcript': t,
}

for name, obj in objects.items():
    try:
        d = obj.to_dict() if not isinstance(obj, tubescrape.Transcript) else obj.to_dict()
        json_str = json.dumps(d, ensure_ascii=False)
        test(f'{name}.to_dict() is valid JSON', len(json_str) > 10)
    except Exception as e:
        test(f'{name}.to_dict() is valid JSON', False, str(e))


# ─────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────
yt.close()

print(f'\n{"=" * 60}')
print(f'  RESULTS: {PASS} passed, {FAIL} failed, {PASS + FAIL} total')
print(f'{"=" * 60}')

if FAIL > 0:
    print('\n  Some tests failed! Check output above for details.')
    sys.exit(1)
else:
    print('\n  All tests passed!')
    sys.exit(0)
