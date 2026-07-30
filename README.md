<h1 align="center">TubeScrape</h1>

<p align="center">
  <strong>Scrape YouTube search results, channels, transcripts, comments, and playlists. No API key needed.</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/tubescrape/"><img src="https://img.shields.io/pypi/v/tubescrape.svg?style=flat-square&color=blue" alt="PyPI version"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%20|%203.11%20|%203.12%20|%203.13-blue.svg?style=flat-square" alt="Python versions"></a>
  <a href="https://github.com/zaidkx37/tubescrape/actions"><img src="https://img.shields.io/github/actions/workflow/status/zaidkx37/tubescrape/ci.yml?style=flat-square&label=CI" alt="CI"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/license-MIT-green.svg?style=flat-square" alt="License: MIT"></a>
  <a href="https://pypi.org/project/tubescrape/"><img src="https://img.shields.io/pypi/dm/tubescrape?style=flat-square&color=orange&label=downloads" alt="Downloads"></a>
</p>

<p align="center">
  <a href="https://zaidkx37.github.io/tubescrape/"><b>Documentation</b></a> · <a href="https://pypi.org/project/tubescrape/"><b>PyPI</b></a> · <a href="https://github.com/zaidkx37/tubescrape/issues"><b>Issues</b></a>
</p>

---

## Install

```bash
pip install tubescrape
```

## Quick Start

```python
from tubescrape import YouTube

yt = YouTube()

# Search
results = yt.search('python tutorial', max_results=5)
for video in results.videos:
    print(video.title, video.view_count, video.is_short)

# Video info with likes, chapters, AI summary
info = yt.get_video_info('https://youtube.com/watch?v=dQw4w9WgXcQ')
print(info.like_count, info.comment_count, info.ai_summary)
for ch in info.chapters:
    print(ch.time_description, ch.title)

# Comments with replies
comments = yt.get_comments('dQw4w9WgXcQ', max_results=10, replies=True)
for c in comments.comments:
    print(c.author, c.text, c.like_count)
    for r in c.replies:
        print(f'  -> {r.author}: {r.text}')

# Channel videos, streams, shorts, playlists, about
videos = yt.get_channel_videos('@lexfridman', max_results=10)
streams = yt.get_channel_streams('@CNN', max_results=5)
shorts = yt.get_channel_shorts('@CNN', max_results=10)
about = yt.get_channel_about('@ycombinator')
print(about.country, about.joined_date, about.subscriber_count)

# Transcript
transcript = yt.get_transcript('dQw4w9WgXcQ')
print(transcript.text)
transcript.save('subtitles.srt')

# Playlist
playlist = yt.get_playlist('PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf')

# Every method accepts URLs, IDs, or @handles
```

## Features

| Feature | What you get |
|---|---|
| **Search** | Videos, channels, shorts with filters (type, duration, date, sort, features) |
| **Video Info** | Title, description, views, likes, comments count, chapters, AI summary, people mentioned |
| **Comments** | Top-level comments with likes, replies, author info, hearted/verified/creator badges |
| **Channel** | Videos, live streams, shorts, playlists, search within channel, about/info page |
| **Transcripts** | Fetch, translate, format (SRT/VTT/JSON), save to file |
| **Playlists** | Full pagination with metadata |
| **Async** | Every method has an `async` variant (`asearch`, `aget_video_info`, etc.) |
| **Proxies** | Rotation, separate transcript proxy pool for mass scraping |

## How It Works

Uses YouTube's internal InnerTube API (the same endpoints the YouTube web client uses). No API key, no OAuth, no Google account required. Only dependency is `httpx`.

## CLI

```bash
pip install "tubescrape[cli]"

tubescrape search "python tutorial" -n 5
tubescrape channel @lexfridman
tubescrape transcript dQw4w9WgXcQ --format srt --save output.srt
```

## REST API

```bash
pip install "tubescrape[api]"

tubescrape serve                    # localhost:8000
```

Swagger docs at `http://localhost:8000/docs`.

## Documentation

For complete API reference, all parameters, return types, code examples, and advanced usage:

**[Read the full documentation](https://zaidkx37.github.io/tubescrape/)**

## Warning

This library uses YouTube's undocumented InnerTube API. It may break if YouTube changes their internal API. If it does, please [open an issue](https://github.com/zaidkx37/tubescrape/issues).

## License

MIT
