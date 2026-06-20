# tubescrape — Complete Usage Guide

A step-by-step guide to every feature in tubescrape. Each section builds on the previous one.

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [1. Searching Videos](#1-searching-videos)
  - [Basic Search](#basic-search)
  - [Filtering by Type](#filtering-by-type)
  - [Filtering by Duration](#filtering-by-duration)
  - [Filtering by Upload Date](#filtering-by-upload-date)
  - [Sorting Results](#sorting-results)
  - [Filtering by Features](#filtering-by-features)
  - [Combining Multiple Filters](#combining-multiple-filters)
- [2. Browsing Channels](#2-browsing-channels)
  - [Channel Videos](#channel-videos)
  - [Channel Shorts](#channel-shorts)
  - [Channel Playlists](#channel-playlists)
  - [Searching Within a Channel](#searching-within-a-channel)
- [3. Fetching Playlists](#3-fetching-playlists)
- [4. Transcripts](#4-transcripts)
  - [Fetching a Transcript](#fetching-a-transcript)
  - [Choosing a Language](#choosing-a-language)
  - [Translating a Transcript](#translating-a-transcript)
  - [Listing Available Languages](#listing-available-languages)
  - [Plain Text (No Timestamps)](#plain-text-no-timestamps)
  - [Formatting (SRT, WebVTT, JSON, Text)](#formatting-srt-webvtt-json-text)
  - [Saving to a File](#saving-to-a-file)
- [5. Working with Results](#5-working-with-results)
  - [Accessing Video Fields](#accessing-video-fields)
  - [Serialization (to_dict / JSON)](#serialization-to_dict--json)
  - [URL Parsing Utilities](#url-parsing-utilities)
- [6. Proxy Support](#6-proxy-support)
  - [Single Proxy](#single-proxy)
  - [Proxy Rotation](#proxy-rotation)
  - [Loading Proxies from a File](#loading-proxies-from-a-file)
- [7. Async Support](#7-async-support)
- [8. Context Managers](#8-context-managers)
- [9. Error Handling](#9-error-handling)
- [10. CLI Usage](#10-cli-usage)
- [11. REST API](#11-rest-api)
- [Data Models Reference](#data-models-reference)
- [Exception Reference](#exception-reference)

---

## Installation

```bash
# Core SDK only (just httpx, no extras)
pip install tubescrape

# With CLI support (adds click + rich)
pip install tubescrape[cli]

# With API server support (adds fastapi + uvicorn)
pip install tubescrape[api]

# Everything
pip install tubescrape[all]

# Development install from source
git clone https://github.com/muhammadzaid/tubescrape.git
cd tubescrape
pip install -e ".[all]"
```

**Requirements:** Python 3.10+

---

## Quick Start

```python
from tubescrape import YouTube

yt = YouTube()

# Search videos
results = yt.search('python tutorial', max_results=5)
for video in results.videos:
    print(f'{video.title} — {video.url}')

# Get a channel's videos
channel = yt.get_channel_videos('@lexfridman', max_results=10)
for video in channel.videos:
    print(f'{video.title} ({video.duration})')

# Fetch a transcript
transcript = yt.get_transcript('dQw4w9WgXcQ')
print(transcript.text)

# Clean up
yt.close()
```

---

## 1. Searching Videos

### Basic Search

```python
from tubescrape import YouTube

yt = YouTube()
results = yt.search('machine learning', max_results=10)

print(f'Query: {results.query}')
print(f'Found: {len(results.videos)} videos\n')

for video in results.videos:
    print(f'{video.title}')
    print(f'  Channel: {video.channel}')
    print(f'  Duration: {video.duration} ({video.duration_seconds}s)')
    print(f'  Views: {video.view_count}')
    print(f'  URL: {video.url}')
    print()
```

### Filtering by Type

Filter results to only show videos, channels, playlists, or movies.

```python
# Only videos (excludes channels, playlists, etc.)
results = yt.search('python', type='video')

# Only playlists
results = yt.search('python course', type='playlist')
```

**Options:** `'video'`, `'channel'`, `'playlist'`, `'movie'`

### Filtering by Duration

```python
# Short videos (under 4 minutes)
results = yt.search('python tips', duration='short')

# Medium videos (4–20 minutes)
results = yt.search('python tutorial', duration='medium')

# Long videos (over 20 minutes)
results = yt.search('python full course', duration='long')
```

**Options:** `'short'` (<4min), `'medium'` (4–20min), `'long'` (>20min)

### Filtering by Upload Date

```python
# Videos uploaded in the last hour
results = yt.search('breaking news', upload_date='last_hour')

# Videos uploaded today
results = yt.search('daily vlog', upload_date='today')

# Videos uploaded this week
results = yt.search('tech news', upload_date='this_week')

# Videos uploaded this month
results = yt.search('monthly recap', upload_date='this_month')

# Videos uploaded this year
results = yt.search('best of', upload_date='this_year')
```

**Options:** `'last_hour'`, `'today'`, `'this_week'`, `'this_month'`, `'this_year'`

### Sorting Results

```python
# By relevance (default)
results = yt.search('python', sort_by='relevance')

# By upload date (newest first)
results = yt.search('python', sort_by='upload_date')

# By view count (most viewed first)
results = yt.search('python', sort_by='view_count')

# By rating (highest rated first)
results = yt.search('python', sort_by='rating')
```

**Options:** `'relevance'`, `'upload_date'`, `'view_count'`, `'rating'`

### Filtering by Features

```python
# Only 4K videos
results = yt.search('nature documentary', features='4k')

# Only HD videos
results = yt.search('tutorial', features='hd')

# Only videos with subtitles
results = yt.search('lecture', features='subtitles')

# Multiple features at once
results = yt.search('music video', features=['4k', 'hdr'])

# Only live streams
results = yt.search('gaming', features='live')
```

**Options:** `'live'`, `'4k'`, `'hd'`, `'subtitles'`, `'cc'`, `'creative_commons'`, `'360'`, `'vr180'`, `'3d'`, `'hdr'`

### Combining Multiple Filters

All filters can be used together:

```python
results = yt.search(
    'podcast interview',
    max_results=10,
    type='video',
    duration='long',
    upload_date='this_month',
    sort_by='view_count',
    features=['hd', 'subtitles'],
)

for video in results.videos:
    print(f'{video.title} — {video.view_count}')
```

---

## 2. Browsing Channels

All channel methods accept any of these formats:

```python
# Channel ID
yt.get_channel_videos('UCJIfeSCssxSC_Dhc5s7woww')

# @handle
yt.get_channel_videos('@lexfridman')

# Full URL
yt.get_channel_videos('https://www.youtube.com/@lexfridman')
yt.get_channel_videos('https://www.youtube.com/channel/UCJIfeSCssxSC_Dhc5s7woww')
```

### Channel Videos

```python
from tubescrape import YouTube

yt = YouTube()

# Get the latest 10 videos
result = yt.get_channel_videos('@lexfridman', max_results=10)

print(f'Channel ID: {result.channel_id}')
print(f'Videos: {len(result.videos)}\n')

for video in result.videos:
    print(f'{video.title}')
    print(f'  Duration: {video.duration}')
    print(f'  Views: {video.view_count}')
    print(f'  Published: {video.published_text}')
    print()
```

Set `max_results=0` to fetch all videos (uses pagination automatically):

```python
all_videos = yt.get_channel_videos('@lexfridman', max_results=0)
print(f'Total videos: {len(all_videos.videos)}')
```

### Channel Shorts

```python
result = yt.get_channel_shorts('@lexfridman')

print(f'Shorts: {len(result.shorts)}\n')

for short in result.shorts:
    print(f'{short.title}')
    print(f'  Views: {short.view_count}')
    print(f'  URL: {short.url}')
    print(f'  Thumbnail: {short.thumbnail_url}')
    print()
```

### Channel Playlists

```python
result = yt.get_channel_playlists('@lexfridman')

print(f'Playlists: {len(result.playlists)}\n')

for playlist in result.playlists:
    print(f'{playlist.title}')
    print(f'  ID: {playlist.playlist_id}')
    print(f'  URL: {playlist.url}')
    print(f'  Videos: {playlist.video_count}')
    print(f'  Thumbnail: {playlist.thumbnail_url}')
    print()
```

### Searching Within a Channel

Search for specific content within a channel's videos:

```python
# Returns all matches (default max_results=0 means no limit)
result = yt.search_channel('@lexfridman', 'artificial intelligence')

# Limit results
result = yt.search_channel('@lexfridman', 'artificial intelligence', max_results=10)

print(f'Found {len(result.videos)} videos matching "{result.query}"\n')

for video in result.videos:
    print(f'{video.title} — {video.duration}')
```

---

## 3. Fetching Playlists

Accepts a playlist ID or full URL:

```python
from tubescrape import YouTube

yt = YouTube()

# By playlist ID
result = yt.get_playlist('PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf')

# By URL
result = yt.get_playlist('https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf')

print(f'Playlist: {result.title}')
print(f'Channel: {result.channel}')
print(f'URL: {result.url}')
print(f'Videos: {len(result.videos)}\n')

for entry in result.videos:
    print(f'#{entry.position}  {entry.title}')
    print(f'    Channel: {entry.channel}')
    print(f'    Duration: {entry.duration} ({entry.duration_seconds}s)')
    print(f'    URL: {entry.url}')
    print()
```

Limit the number of videos fetched:

```python
# Only the first 5 videos
result = yt.get_playlist('PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf', max_results=5)
```

---

## 4. Transcripts

### Fetching a Transcript

Accepts a video ID or any YouTube URL format:

```python
from tubescrape import YouTube

yt = YouTube()

# By video ID
transcript = yt.get_transcript('dQw4w9WgXcQ')

# By URL
transcript = yt.get_transcript('https://www.youtube.com/watch?v=dQw4w9WgXcQ')

# By short URL
transcript = yt.get_transcript('https://youtu.be/dQw4w9WgXcQ')

# Access the full text
print(transcript.text)

# Access metadata
print(f'Language: {transcript.language} ({transcript.language_code})')
print(f'Auto-generated: {transcript.is_generated}')
print(f'Segments: {len(transcript.segments)}')

# Iterate over segments
for segment in transcript.segments:
    print(f'[{segment.start:.1f}s] {segment.text}')
```

### Choosing a Language

Pass a list of preferred language codes. The first available match is used:

```python
# Prefer German, fall back to English
transcript = yt.get_transcript('dQw4w9WgXcQ', languages=['de', 'en'])
print(f'Got: {transcript.language} ({transcript.language_code})')

# Prefer Japanese
transcript = yt.get_transcript('dQw4w9WgXcQ', languages=['ja'])

# Default is ['en'] if not specified
transcript = yt.get_transcript('dQw4w9WgXcQ')
```

### Translating a Transcript

Translate the transcript into another language (if the video supports it):

```python
# Translate to Spanish
transcript = yt.get_transcript('dQw4w9WgXcQ', translate_to='es')
print(f'Translation: {transcript.translation_language}')
print(transcript.text)

# Translate to French
transcript = yt.get_transcript('dQw4w9WgXcQ', translate_to='fr')

# Translate to Japanese
transcript = yt.get_transcript('dQw4w9WgXcQ', translate_to='ja')
```

If the translation language is not available, a `TranslationNotAvailableError` is raised.

### Listing Available Languages

Check which transcript languages are available for a video:

```python
entries = yt.list_transcripts('dQw4w9WgXcQ')

for entry in entries:
    kind = 'auto-generated' if entry.is_generated else 'manual'
    translatable = ', translatable' if entry.is_translatable else ''
    print(f'{entry.language} ({entry.language_code}) — {kind}{translatable}')
```

Output:
```
English (en) — manual, translatable
English (auto-generated) (en) — auto-generated, translatable
German (Germany) (de-DE) — manual, translatable
Japanese (ja) — manual, translatable
Portuguese (Brazil) (pt-BR) — manual, translatable
Spanish (Latin America) (es-419) — manual, translatable
```

### Plain Text (No Timestamps)

Get the transcript as a single block of text without timing information:

```python
# Option 1: via parameter
transcript = yt.get_transcript('dQw4w9WgXcQ', timestamps=False)
print(transcript.text)
# Only 1 segment with the full text, start=0.0, duration=0.0

# Option 2: strip timestamps from an existing transcript
transcript = yt.get_transcript('dQw4w9WgXcQ')
plain = transcript.without_timestamps()
print(plain.text)
```

### Formatting (SRT, WebVTT, JSON, Text)

Format a transcript into common subtitle/text formats:

```python
transcript = yt.get_transcript('dQw4w9WgXcQ')

# Plain text — all segments joined
text = YouTube.format_transcript(transcript, fmt='text')
print(text)

# SRT subtitle format
srt = YouTube.format_transcript(transcript, fmt='srt')
print(srt)
# 1
# 00:00:01,360 --> 00:00:03,040
# [♪♪♪]
#
# 2
# 00:00:18,640 --> 00:00:21,880
# ♪ We're no strangers to love ♪

# WebVTT format
vtt = YouTube.format_transcript(transcript, fmt='vtt')
print(vtt)
# WEBVTT
#
# 00:00:01.360 --> 00:00:03.040
# [♪♪♪]

# JSON format
json_str = YouTube.format_transcript(transcript, fmt='json')
print(json_str)
# {"video_id": "dQw4w9WgXcQ", "language": "English", ...}
```

**Formats:** `'text'`, `'json'`, `'srt'`, `'vtt'` (or `'webvtt'`)

### Saving to a File

Save a transcript directly to disk. The format is inferred from the file extension:

```python
transcript = yt.get_transcript('dQw4w9WgXcQ')

# Format inferred from extension
transcript.save('subtitles.srt')     # → saves as SRT
transcript.save('subtitles.vtt')     # → saves as WebVTT
transcript.save('transcript.json')   # → saves as JSON
transcript.save('transcript.txt')    # → saves as plain text

# Explicit format (extension added automatically if missing)
path = transcript.save('output', format='srt')
print(path)  # → output.srt

# Returns a Path object
path = transcript.save('my_transcript.srt')
print(f'Saved to {path} ({path.stat().st_size} bytes)')
```

---

## 5. Working with Results

### Accessing Video Fields

Every `VideoResult` has these fields:

```python
results = yt.search('python', max_results=1)
video = results.videos[0]

# Always present
video.video_id          # 'kqtD5dpn9C8'
video.title             # 'Python for Beginners'
video.channel           # 'Programming with Mosh'
video.channel_id        # 'UCWv7vMbMWH4-V0ZXdmDpPBA'
video.duration          # '1:00:06'
video.duration_seconds  # 3606
video.published_text    # '5 years ago'
video.url               # 'https://www.youtube.com/watch?v=kqtD5dpn9C8'
video.is_live           # False
video.is_short          # False

# Optional (may be None or empty)
video.view_count        # '23M views'
video.short_view_count  # '23M'
video.thumbnails        # [Thumbnail(url=..., width=..., height=...), ...]
video.thumbnail_url     # Highest-res thumbnail URL (property)
video.moving_thumbnail  # Animated preview URL
video.channel_thumbnail # Channel avatar URL
video.description_snippet  # Truncated description text
video.is_verified       # False
video.badges            # ['CC'] or []
video.channel_url       # 'https://www.youtube.com/channel/UCWv7...' (property)
```

### Serialization (to_dict / JSON)

All result objects have a `to_dict()` method for easy serialization:

```python
import json

# Search results
results = yt.search('python', max_results=2)
data = results.to_dict()
print(json.dumps(data, indent=2))
# {"query": "python", "videos": [{...}, {...}]}

# Single video (sparse — optional fields excluded when empty)
video = results.videos[0]
data = video.to_dict()
# Keys like "is_verified" are excluded when False
# Keys like "badges" are excluded when empty

# Transcript
transcript = yt.get_transcript('dQw4w9WgXcQ')
data = transcript.to_dict()
# {"video_id": "...", "language": "...", "segments": [...], "text": "..."}

# Transcript without timestamps
data = transcript.to_dict(timestamps=False)
# {"video_id": "...", "language": "...", "text": "..."}  (no "segments" key)

# Channel shorts
shorts = yt.get_channel_shorts('@lexfridman')
data = shorts.to_dict()
# {"channel_id": "...", "shorts": [{...}, ...]}

# Playlist
playlist = yt.get_playlist('PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf')
data = playlist.to_dict()
# {"playlist_id": "...", "title": "...", "channel": "...", "videos": [...], "url": "..."}
```

### URL Parsing Utilities

Extract IDs from any YouTube URL format without making network requests:

```python
from tubescrape import YouTube

# Video ID extraction
YouTube.extract_video_id('dQw4w9WgXcQ')                                        # → 'dQw4w9WgXcQ'
YouTube.extract_video_id('https://www.youtube.com/watch?v=dQw4w9WgXcQ')         # → 'dQw4w9WgXcQ'
YouTube.extract_video_id('https://youtu.be/dQw4w9WgXcQ')                        # → 'dQw4w9WgXcQ'
YouTube.extract_video_id('https://www.youtube.com/embed/dQw4w9WgXcQ')           # → 'dQw4w9WgXcQ'
YouTube.extract_video_id('https://www.youtube.com/shorts/dQw4w9WgXcQ')          # → 'dQw4w9WgXcQ'
YouTube.extract_video_id('https://www.youtube.com/live/dQw4w9WgXcQ')            # → 'dQw4w9WgXcQ'
YouTube.extract_video_id('https://m.youtube.com/watch?v=dQw4w9WgXcQ')           # → 'dQw4w9WgXcQ'
YouTube.extract_video_id('https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s')   # → 'dQw4w9WgXcQ'

# Channel ID extraction
YouTube.extract_channel_id('UCJIfeSCssxSC_Dhc5s7woww')                                  # → 'UCJIfeSCssxSC_Dhc5s7woww'
YouTube.extract_channel_id('https://www.youtube.com/channel/UCJIfeSCssxSC_Dhc5s7woww')   # → 'UCJIfeSCssxSC_Dhc5s7woww'
YouTube.extract_channel_id('@lexfridman')                                                # → '@lexfridman'
YouTube.extract_channel_id('https://www.youtube.com/@lexfridman')                        # → '@lexfridman'

# Playlist ID extraction
YouTube.extract_playlist_id('PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf')                                          # → 'PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf'
YouTube.extract_playlist_id('https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf')     # → 'PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf'
YouTube.extract_playlist_id('https://www.youtube.com/watch?v=abc&list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf')  # → 'PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf'

# Invalid inputs raise ValueError
try:
    YouTube.extract_video_id('')
except ValueError as e:
    print(e)  # Could not extract video ID from: ...
```

---

## 6. Proxy Support

### Single Proxy

```python
yt = YouTube(proxy='http://user:password@proxy.example.com:8080')

results = yt.search('python')
```

### Proxy Rotation

Pass a list of proxies. Each request cycles to the next proxy automatically:

```python
yt = YouTube(proxies=[
    'http://user:pass@proxy1.example.com:8080',
    'http://user:pass@proxy2.example.com:8080',
    'http://user:pass@proxy3.example.com:8080',
])

# Each request uses the next proxy in the list
results = yt.search('python')          # → proxy1
transcript = yt.get_transcript('...')  # → proxy2
channel = yt.get_channel_videos('...') # → proxy3
# Wraps back to proxy1 after the list is exhausted
```

### Separate Transcript Proxy Pool

YouTube's player and caption endpoints are much stricter about datacenter IPs than search/browse. You can supply dedicated residential proxies for transcripts while using cheaper datacenter proxies for everything else:

```python
# Datacenter proxies for search/browse (cheap, fast)
# Residential proxies for transcripts (reliable, avoids captcha)
yt = YouTube(
    proxies=[
        'http://dc-user:pass@datacenter1:8080',
        'http://dc-user:pass@datacenter2:8080',
    ],
    transcript_proxies=[
        'http://res-user:pass@residential1:8080',
        'http://res-user:pass@residential2:8080',
    ],
)

# Or a single transcript proxy
yt = YouTube(
    proxy='http://dc-proxy:8080',
    transcript_proxy='http://residential-proxy:8080',
)

# If no transcript proxies are set, the main proxies are used for everything
```

### Loading Proxies from a File

Proxy files use `host:port:username:password` format, one per line:

```
# proxies/brightdata.txt
brd.superproxy.io:33335:brd-customer-xxx:password123
brd.superproxy.io:33335:brd-customer-yyy:password456
```

Load them like this:

```python
def load_proxies(filepath):
    proxies = []
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            host, port, user, password = line.split(':')
            proxies.append(f'http://{user}:{password}@{host}:{port}')
    return proxies

proxies = load_proxies('proxies/brightdata.txt')
yt = YouTube(proxies=proxies)
```

You can also set a proxy via environment variable for the CLI:

```bash
export TUBESCRAPE_PROXY="http://user:pass@host:port"
tubescrape search "python"
```

---

## 7. Async Support

Every method has an async variant prefixed with `a`:

```python
import asyncio
from tubescrape import YouTube

async def main():
    yt = YouTube()

    # Search
    results = await yt.asearch('python', max_results=5)
    for v in results.videos:
        print(v.title)

    # Channel videos
    channel = await yt.aget_channel_videos('@lexfridman', max_results=5)

    # Channel shorts
    shorts = await yt.aget_channel_shorts('@lexfridman')

    # Channel playlists
    playlists = await yt.aget_channel_playlists('@lexfridman')

    # Search within channel
    search = await yt.asearch_channel('@lexfridman', 'AI')

    # Playlist
    playlist = await yt.aget_playlist('PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf')

    # Transcript
    transcript = await yt.aget_transcript('dQw4w9WgXcQ')
    print(transcript.text)

    # Translated transcript
    transcript = await yt.aget_transcript('dQw4w9WgXcQ', translate_to='es')

    # List transcript languages
    languages = await yt.alist_transcripts('dQw4w9WgXcQ')

    await yt.aclose()

asyncio.run(main())
```

Run multiple requests concurrently with `asyncio.gather`:

```python
async def fetch_multiple():
    yt = YouTube()

    results = await asyncio.gather(
        yt.asearch('python'),
        yt.asearch('javascript'),
        yt.asearch('rust programming'),
    )

    for result in results:
        print(f'{result.query}: {len(result.videos)} videos')

    await yt.aclose()

asyncio.run(fetch_multiple())
```

---

## 8. Context Managers

Automatically close HTTP connections when done:

```python
from tubescrape import YouTube

# Sync
with YouTube() as yt:
    results = yt.search('python')
    print(len(results.videos))
# Client is automatically closed here

# Async
import asyncio

async def main():
    async with YouTube() as yt:
        results = await yt.asearch('python')
        print(len(results.videos))
    # Client is automatically closed here

asyncio.run(main())
```

---

## 9. Error Handling

```python
from tubescrape import (
    YouTube,
    YouTubeError,
    VideoUnavailableError,
    TranscriptsDisabledError,
    TranscriptsNotAvailableError,
    TranslationNotAvailableError,
    ChannelNotFoundError,
    PlaylistNotFoundError,
    RateLimitError,
    ProxyBlockedError,
    CaptchaError,
    BotDetectedError,
    RequestError,
)

yt = YouTube()

# Catch a specific error
try:
    transcript = yt.get_transcript('xxxxxxxxxxx')
except TranscriptsDisabledError as e:
    print(f'Transcripts disabled: {e}')
except VideoUnavailableError as e:
    print(f'Video unavailable: {e}')

# Catch translation errors
try:
    transcript = yt.get_transcript('dQw4w9WgXcQ', translate_to='nonexistent')
except TranslationNotAvailableError as e:
    print(f'Translation not available: {e}')

# Catch channel errors
try:
    videos = yt.get_channel_videos('https://www.youtube.com/channel/UC_FAKE_CHANNEL')
except ChannelNotFoundError as e:
    print(f'Channel not found: {e}')

# Catch rate limiting
try:
    results = yt.search('python')
except RateLimitError:
    print('Rate limited (retried automatically, still failing)')

# Catch proxy blocks (datacenter IP rejected by firewall)
try:
    results = yt.search('python')
except ProxyBlockedError:
    print('Proxy blocked by firewall, switch to residential proxies')

# Catch captcha (YouTube bot verification challenge)
try:
    transcript = yt.get_transcript('dQw4w9WgXcQ')
except CaptchaError:
    print('Captcha triggered, use residential proxies for transcripts')

# Catch bot detection
try:
    results = yt.search('python')
except BotDetectedError:
    print('Bot detected, use a proxy')

# Catch any tubescrape error
try:
    results = yt.search('python')
except YouTubeError as e:
    print(f'Something went wrong: {e}')

# All tubescrape errors inherit from YouTubeError
assert issubclass(VideoUnavailableError, YouTubeError)
assert issubclass(TranscriptsDisabledError, YouTubeError)
assert issubclass(RateLimitError, YouTubeError)
assert issubclass(BotDetectedError, YouTubeError)

yt.close()
```

---

## 10. CLI Usage

The CLI is available after installing with `pip install tubescrape[cli]`.

### Search

```bash
# Basic search
tubescrape search "python tutorial"

# Limit results
tubescrape search "python" -n 5

# With filters
tubescrape search "podcast" --type video --duration long
tubescrape search "news" --upload-date today --sort-by view_count
tubescrape search "music" --features 4k --features hdr

# JSON output (for piping to jq, etc.)
tubescrape search "python" --json
```

### Channel

```bash
# Browse a channel's videos (default)
tubescrape channel @lexfridman
tubescrape channel @lexfridman -n 10

# Browse shorts
tubescrape channel @lexfridman shorts

# Browse playlists
tubescrape channel @lexfridman playlists

# Search within a channel
tubescrape channel @lexfridman search "artificial intelligence"

# JSON output
tubescrape channel @lexfridman --json
tubescrape channel @lexfridman shorts --json
```

### Playlist

```bash
# Fetch a playlist
tubescrape playlist PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf

# Limit videos
tubescrape playlist PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf -n 5

# JSON output
tubescrape playlist PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf --json
```

### Transcript

```bash
# Fetch transcript (plain text)
tubescrape transcript dQw4w9WgXcQ

# SRT format
tubescrape transcript dQw4w9WgXcQ --format srt

# WebVTT format
tubescrape transcript dQw4w9WgXcQ --format vtt

# JSON format
tubescrape transcript dQw4w9WgXcQ --format json

# Without timestamps
tubescrape transcript dQw4w9WgXcQ --no-timestamps

# Specific language
tubescrape transcript dQw4w9WgXcQ --lang de

# Multiple language fallback
tubescrape transcript dQw4w9WgXcQ --lang ja --lang en

# Translate
tubescrape transcript dQw4w9WgXcQ --translate es

# Save to file
tubescrape transcript dQw4w9WgXcQ --save subtitles.srt

# List available languages
tubescrape transcript dQw4w9WgXcQ --list-languages
tubescrape transcript dQw4w9WgXcQ --list-languages --json
```

### Global Options

```bash
# Use a proxy
tubescrape --proxy http://user:pass@host:port search "python"

# Show version
tubescrape --version
```

---

## 11. REST API

Start the API server after installing with `pip install tubescrape[api]`:

```bash
tubescrape serve
tubescrape serve --host 0.0.0.0 --port 8000
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/search?q=...` | Search videos |
| GET | `/api/v1/channel/{id}/videos` | Browse channel videos |
| GET | `/api/v1/channel/{id}/shorts` | Browse channel shorts |
| GET | `/api/v1/channel/{id}/playlists` | Browse channel playlists |
| GET | `/api/v1/channel/{id}/search?q=...` | Search within a channel |
| GET | `/api/v1/transcript/{video_id}` | Fetch transcript |
| GET | `/api/v1/transcript/{video_id}/languages` | List transcript languages |
| GET | `/health` | Health check |

### Search

```bash
# Basic search
curl "http://localhost:8000/api/v1/search?q=python"

# With filters
curl "http://localhost:8000/api/v1/search?q=podcast&type=video&duration=long&max_results=5"

# With sorting
curl "http://localhost:8000/api/v1/search?q=news&upload_date=today&sort_by=view_count"

# With features
curl "http://localhost:8000/api/v1/search?q=music&features=4k,hdr"
```

### Channel

```bash
# Channel videos
curl "http://localhost:8000/api/v1/channel/UCJIfeSCssxSC_Dhc5s7woww/videos?max_results=10"

# Channel shorts
curl "http://localhost:8000/api/v1/channel/UCJIfeSCssxSC_Dhc5s7woww/shorts"

# Channel playlists
curl "http://localhost:8000/api/v1/channel/UCJIfeSCssxSC_Dhc5s7woww/playlists"

# Search within channel
curl "http://localhost:8000/api/v1/channel/UCJIfeSCssxSC_Dhc5s7woww/search?q=AI"
```

### Transcript

```bash
# JSON format (default)
curl "http://localhost:8000/api/v1/transcript/dQw4w9WgXcQ"

# SRT format
curl "http://localhost:8000/api/v1/transcript/dQw4w9WgXcQ?format=srt"

# WebVTT format
curl "http://localhost:8000/api/v1/transcript/dQw4w9WgXcQ?format=vtt"

# Specific language
curl "http://localhost:8000/api/v1/transcript/dQw4w9WgXcQ?lang=de"

# Translate
curl "http://localhost:8000/api/v1/transcript/dQw4w9WgXcQ?translate_to=es"

# Without timestamps
curl "http://localhost:8000/api/v1/transcript/dQw4w9WgXcQ?timestamps=false"

# List available languages
curl "http://localhost:8000/api/v1/transcript/dQw4w9WgXcQ/languages"
```

### Interactive Docs

Visit `http://localhost:8000/docs` for the auto-generated Swagger UI where you can test all endpoints interactively.

---

## Data Models Reference

All models are frozen dataclasses (`@dataclass(frozen=True, slots=True)`) with `.to_dict()` for serialization.

### `VideoResult`

Returned by `search()`, `get_channel_videos()`, `search_channel()`.

| Field | Type | Description |
|-------|------|-------------|
| `video_id` | `str` | YouTube video ID |
| `title` | `str` | Video title |
| `channel` | `str` | Channel name |
| `channel_id` | `str \| None` | Channel ID (UC...) |
| `duration` | `str \| None` | Human-readable duration (`"12:34"`) |
| `duration_seconds` | `int` | Duration in seconds |
| `published_text` | `str \| None` | Relative publish time (`"2 days ago"`) |
| `url` | `str` | Full YouTube video URL |
| `is_live` | `bool` | Whether this is a live stream |
| `is_short` | `bool` | Whether this is a YouTube Short |
| `view_count` | `str \| None` | Full view count (`"18,044,188 views"`) |
| `short_view_count` | `str \| None` | Abbreviated views (`"18M views"`) |
| `thumbnails` | `list[Thumbnail]` | Video thumbnails (multiple sizes) |
| `moving_thumbnail` | `str \| None` | Animated preview URL (webp) |
| `channel_thumbnail` | `str \| None` | Channel avatar URL |
| `description_snippet` | `str \| None` | Truncated description text |
| `is_verified` | `bool` | Channel has a verified badge |
| `badges` | `list[str]` | Video badges (`["CC", "New", "4K"]`) |

**Properties:** `thumbnail_url` (highest-res thumbnail), `channel_url`

### `SearchResult`

| Field | Type | Description |
|-------|------|-------------|
| `query` | `str` | Original search query |
| `videos` | `list[VideoResult]` | Matched videos |

### `BrowseResult`

| Field | Type | Description |
|-------|------|-------------|
| `channel_id` | `str` | Channel ID |
| `videos` | `list[VideoResult]` | Channel's videos |

### `ShortResult`

| Field | Type | Description |
|-------|------|-------------|
| `video_id` | `str` | Video ID |
| `title` | `str` | Short title |
| `view_count` | `str \| None` | View count (`"10K views"`) |
| `thumbnail_url` | `str \| None` | Thumbnail URL |

**Properties:** `url` (YouTube Shorts URL)

### `ShortsResult`

| Field | Type | Description |
|-------|------|-------------|
| `channel_id` | `str` | Channel ID |
| `shorts` | `list[ShortResult]` | Channel's Shorts |

### `ChannelPlaylistEntry`

| Field | Type | Description |
|-------|------|-------------|
| `playlist_id` | `str` | Playlist ID |
| `title` | `str` | Playlist title |
| `thumbnail_url` | `str \| None` | Cover thumbnail |
| `video_count` | `str \| None` | Number of videos (`"25 videos"`) |

**Properties:** `url` (YouTube playlist URL)

### `ChannelPlaylistsResult`

| Field | Type | Description |
|-------|------|-------------|
| `channel_id` | `str` | Channel ID |
| `playlists` | `list[ChannelPlaylistEntry]` | Channel's playlists |

### `PlaylistEntry`

| Field | Type | Description |
|-------|------|-------------|
| `video_id` | `str` | Video ID |
| `title` | `str` | Video title |
| `channel` | `str` | Channel name |
| `duration` | `str \| None` | Human-readable duration |
| `duration_seconds` | `int` | Duration in seconds |
| `position` | `int` | Position in playlist (1-based) |
| `url` | `str` | Full video URL |
| `thumbnails` | `list[Thumbnail]` | Thumbnails |

**Properties:** `thumbnail_url` (highest-res thumbnail)

### `PlaylistResult`

| Field | Type | Description |
|-------|------|-------------|
| `playlist_id` | `str` | Playlist ID |
| `title` | `str \| None` | Playlist title |
| `channel` | `str \| None` | Playlist creator |
| `videos` | `list[PlaylistEntry]` | Videos in playlist |

**Properties:** `url` (YouTube playlist URL)

### `Thumbnail`

| Field | Type | Description |
|-------|------|-------------|
| `url` | `str` | Image URL |
| `width` | `int` | Width in pixels |
| `height` | `int` | Height in pixels |

### `Transcript`

| Field | Type | Description |
|-------|------|-------------|
| `video_id` | `str` | Video ID |
| `language` | `str` | Language name (`"English"`) |
| `language_code` | `str` | Language code (`"en"`) |
| `is_generated` | `bool` | Auto-generated or manual |
| `segments` | `list[TranscriptSegment]` | Timed text segments |
| `translation_language` | `str \| None` | Translation target language |

**Properties:** `text` (all segments joined)
**Methods:** `save(filename, format=None)`, `without_timestamps()`, `to_dict(timestamps=True)`

### `TranscriptSegment`

| Field | Type | Description |
|-------|------|-------------|
| `text` | `str` | Segment text |
| `start` | `float` | Start time in seconds |
| `duration` | `float` | Duration in seconds |

### `TranscriptListEntry`

| Field | Type | Description |
|-------|------|-------------|
| `language` | `str` | Language name |
| `language_code` | `str` | Language code |
| `is_generated` | `bool` | Auto-generated or manual |
| `is_translatable` | `bool` | Can be translated |

### Quick Reference Table

| Model | Fields | Used By |
|-------|--------|---------|
| `VideoResult` | `video_id`, `title`, `channel`, `channel_id`, `duration`, `duration_seconds`, `published_text`, `url`, `is_live`, `is_short`, `view_count`, `short_view_count`, `thumbnails`, `moving_thumbnail`, `channel_thumbnail`, `description_snippet`, `is_verified`, `badges` | `search()`, `get_channel_videos()`, `search_channel()` |
| `SearchResult` | `query`, `videos: list[VideoResult]` | `search()`, `search_channel()` |
| `BrowseResult` | `channel_id`, `videos: list[VideoResult]` | `get_channel_videos()` |
| `ShortResult` | `video_id`, `title`, `view_count`, `thumbnail_url`, `url` (property) | `get_channel_shorts()` |
| `ShortsResult` | `channel_id`, `shorts: list[ShortResult]` | `get_channel_shorts()` |
| `ChannelPlaylistEntry` | `playlist_id`, `title`, `thumbnail_url`, `video_count`, `url` (property) | `get_channel_playlists()` |
| `ChannelPlaylistsResult` | `channel_id`, `playlists: list[ChannelPlaylistEntry]` | `get_channel_playlists()` |
| `PlaylistEntry` | `video_id`, `title`, `channel`, `duration`, `duration_seconds`, `position`, `url`, `thumbnails` | `get_playlist()` |
| `PlaylistResult` | `playlist_id`, `title`, `channel`, `videos: list[PlaylistEntry]`, `url` (property) | `get_playlist()` |
| `Transcript` | `video_id`, `language`, `language_code`, `is_generated`, `segments: list[TranscriptSegment]`, `translation_language`, `text` (property) | `get_transcript()` |
| `TranscriptSegment` | `text`, `start`, `duration` | Inside `Transcript.segments` |
| `TranscriptListEntry` | `language`, `language_code`, `is_generated`, `is_translatable` | `list_transcripts()` |
| `Thumbnail` | `url`, `width`, `height` | Inside `VideoResult.thumbnails`, `PlaylistEntry.thumbnails` |

All models are **frozen dataclasses** (immutable) with `to_dict()` for serialization.

---

## Exception Reference

```
YouTubeError                        Base exception for all errors
├── RequestError                    HTTP request failed after retries
│   ├── RateLimitError              HTTP 429, auto-retried with backoff
│   ├── ProxyBlockedError           Proxy firewall block, auto-retried with rotation
│   ├── CaptchaError                Bot verification challenge, auto-retried with rotation
│   └── BotDetectedError            HTTP 403, automated access detected
├── VideoUnavailableError           Video is deleted, private, or region-locked
│   └── AgeRestrictedError          Video requires age verification
├── TranscriptsDisabledError        Transcripts are disabled for this video
├── TranscriptsNotAvailableError    No transcripts in the requested language
├── TranscriptFetchError            Failed to fetch or parse transcript content
├── TranslationNotAvailableError    Translation language not available
├── ChannelNotFoundError            Channel ID or handle could not be resolved
├── PlaylistNotFoundError           Playlist not found or empty
├── APIKeyNotFoundError             InnerTube API key not found on watch page
└── ParsingError                    Failed to parse YouTube response
```

**Auto-retry behavior:** `RateLimitError`, `ProxyBlockedError`, and server errors (500/502/503/504) are automatically retried with exponential backoff. `CaptchaError` is retried with proxy rotation during transcript fetching. Network errors (timeouts, SSL, connection resets) trigger an automatic client reset and retry. Only raised to the caller after all retry attempts are exhausted.

All exceptions inherit from `YouTubeError`, so you can catch everything with a single `except YouTubeError`.
