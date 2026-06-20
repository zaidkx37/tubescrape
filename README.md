<h1 align="center">TubeScrape</h1>

<p align="center">
  <strong>Scrape YouTube search results, channels, transcripts, and playlists — no API key needed.</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/tubescrape/"><img src="https://img.shields.io/pypi/v/tubescrape.svg?style=flat-square&color=blue" alt="PyPI version"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%20|%203.11%20|%203.12%20|%203.13-blue.svg?style=flat-square" alt="Python versions"></a>
  <a href="https://github.com/zaidkx37/tubescrape/actions"><img src="https://img.shields.io/github/actions/workflow/status/zaidkx37/tubescrape/ci.yml?style=flat-square&label=CI" alt="CI"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/license-MIT-green.svg?style=flat-square" alt="License: MIT"></a>
  <a href="https://pypi.org/project/tubescrape/"><img src="https://img.shields.io/pypi/dm/tubescrape?style=flat-square&color=orange&label=downloads" alt="Downloads"></a>
</p>

<p align="center">
  Built on YouTube's internal InnerTube API. Three interfaces: <b>Python SDK</b>, <b>CLI</b>, and <b>REST API</b>.
</p>

---

## Features

- **Search** with filters — type, duration, upload date, sort order, features (4K, HDR, live, CC)
- **Channel browsing** — videos, shorts, playlists, and in-channel search
- **Transcripts** — fetch, translate, format (SRT / WebVTT / JSON), save to file
- **Playlists** — full pagination with position tracking and metadata
- **Async-first** — every method has an `async` variant for concurrent workloads
- **JSON-ready** — every result object has `.to_dict()` for instant serialization
- **Proxy rotation** — built-in support with separate transcript proxy pool for mass scraping
- **Production-ready** — auto-retry on rate limits, 5xx errors, captcha, and proxy blocks
- **Three interfaces** — Python SDK, CLI with Rich tables, REST API with Swagger docs
- **Zero config** — no API key, no OAuth, no setup
- **Lightweight** — only `httpx` as a core dependency

---

## Installation
recommended to **[install using pip](https://pypi.org/project/tubescrape/)**

You can also integrate it into an existing [project](https://github.com/zaidkx37/tubescrape#api) or use it via a [CLI](https://github.com/zaidkx37/tubescrape#cli).

```bash
# Core SDK only
pip install tubescrape

# With CLI (adds click + rich)
pip install "tubescrape[cli]"

# With REST API server (adds fastapi + uvicorn)
pip install "tubescrape[api]"

# Everything
pip install "tubescrape[all]"
```

**Requirements:** Python 3.10+

---

## Quick Start

```python
import json
from tubescrape import YouTube

with YouTube() as yt:
    # Search YouTube
    results = yt.search('python tutorial', max_results=5)
    for video in results.videos:
        print(f'{video.title} — {video.duration} — {video.view_count}')

    # Browse a channel
    channel = yt.get_channel_videos('@lexfridman', max_results=10)
    for video in channel.videos:
        print(f'{video.title} ({video.published_text})')

    # Get a transcript and save as subtitles
    transcript = yt.get_transcript('dQw4w9WgXcQ')
    print(transcript.text)
    transcript.save('subtitles.srt')

    # Every result serializes to JSON instantly
    data = results.to_dict()
    print(json.dumps(data, indent=2))
```

> Every method accepts plain IDs, full URLs, or @handles — parsed automatically.

---

## Why tubescrape?

| | tubescrape | youtube-transcript-api | pytube / pytubefix | yt-dlp |
|---|:---:|:---:|:---:|:---:|
| Search videos | **Yes** | No | No | Limited |
| Channel browse | **Yes** | No | No | Yes |
| Transcripts | **Yes** | Yes | No | Yes |
| Playlists | **Yes** | No | Yes | Yes |
| Async support | **Yes** | No | No | No |
| Built-in REST API | **Yes** | No | No | No |
| CLI tool | **Yes** | No | No | Yes |
| Core dependencies | **1** (httpx) | 1 (requests) | 0 | Many |
| API key needed | **No** | No | No | No |

---

## Search

```python
results = yt.search('python tutorial', max_results=5)

for video in results.videos:
    print(f'{video.title} — {video.url}')
    print(f'  {video.view_count} | {video.duration} | {video.published_text}')
    print(f'  Channel: {video.channel} (verified: {video.is_verified})')
```

### Search Filters

All filters can be combined in a single call:

```python
results = yt.search(
    'podcast interview',
    max_results=10,
    type='video',              # video | channel | playlist | movie
    duration='long',           # short (<4m) | medium (4-20m) | long (>20m)
    upload_date='this_month',  # last_hour | today | this_week | this_month | this_year
    sort_by='view_count',      # relevance | upload_date | view_count | rating
    features=['hd', 'subtitles'],  # live | 4k | hd | subtitles | cc | creative_commons | 360 | vr180 | 3d | hdr
)
```

---

## Channel Browsing

All channel methods accept `@handle`, channel ID (`UC...`), or full URL.

```python
# Videos (newest first, with pagination)
videos = yt.get_channel_videos('@lexfridman', max_results=10)
all_videos = yt.get_channel_videos('@lexfridman', max_results=0)  # fetch ALL

# Shorts
shorts = yt.get_channel_shorts('@lexfridman')
for short in shorts.shorts:
    print(f'{short.title} — {short.view_count} — {short.url}')

# Playlists
playlists = yt.get_channel_playlists('@lexfridman')
for pl in playlists.playlists:
    print(f'{pl.title} — {pl.video_count} — {pl.url}')

# Search within a channel
results = yt.search_channel('@lexfridman', 'artificial intelligence', max_results=10)
```

---

## Transcripts

```python
# Fetch transcript (auto-detects best language)
transcript = yt.get_transcript('dQw4w9WgXcQ')
print(transcript.text)  # full text as a single string

# Choose language (priority order fallback)
transcript = yt.get_transcript('dQw4w9WgXcQ', languages=['de', 'en'])

# Translate to any language
transcript = yt.get_transcript('dQw4w9WgXcQ', translate_to='es')

# Without timestamps (plain text blob)
transcript = yt.get_transcript('dQw4w9WgXcQ', timestamps=False)

# List available languages
languages = yt.list_transcripts('dQw4w9WgXcQ')
for entry in languages:
    print(f'{entry.language} ({entry.language_code}) — {"auto" if entry.is_generated else "manual"}')
```

### Formatting & Saving

```python
transcript = yt.get_transcript('dQw4w9WgXcQ')

# Format as SRT, WebVTT, JSON, or plain text
srt = YouTube.format_transcript(transcript, fmt='srt')
vtt = YouTube.format_transcript(transcript, fmt='vtt')

# Save to file (format auto-detected from extension)
transcript.save('subtitles.srt')
transcript.save('subtitles.vtt')
transcript.save('transcript.json')
transcript.save('transcript.txt')
```

---

## Playlists

```python
# Accepts playlist ID or full URL
playlist = yt.get_playlist('PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf')

print(f'{playlist.title} by {playlist.channel} — {len(playlist.videos)} videos')

for entry in playlist.videos:
    print(f'#{entry.position}  {entry.title} — {entry.duration}')
```

---

## Serialization (`.to_dict()`)

Every result object converts to a plain Python dictionary — ready for JSON, databases, or APIs:

```python
import json

# Works on every result type
results.to_dict()       # SearchResult → dict
video.to_dict()         # VideoResult → dict
channel.to_dict()       # BrowseResult → dict
shorts.to_dict()        # ShortsResult → dict
playlists.to_dict()     # ChannelPlaylistsResult → dict
playlist.to_dict()      # PlaylistResult → dict
transcript.to_dict()    # Transcript → dict

# Sparse output: optional fields excluded when empty/default
# is_verified=False → omitted | badges=[] → omitted | None fields → omitted
print(json.dumps(results.to_dict(), indent=2, ensure_ascii=False))
```

---

## Async Support

Every method has an async variant prefixed with `a`. Use in FastAPI, Discord bots, or any async application:

```python
import asyncio
from tubescrape import YouTube

async def main():
    async with YouTube() as yt:
        # All methods have async variants
        results = await yt.asearch('python', max_results=5)
        transcript = await yt.aget_transcript('dQw4w9WgXcQ')

        # Run multiple requests concurrently
        r1, r2, r3 = await asyncio.gather(
            yt.asearch('python'),
            yt.asearch('javascript'),
            yt.asearch('rust'),
        )

asyncio.run(main())
```

---

## Proxy Support

```python
# Single proxy
yt = YouTube(proxy='http://user:pass@proxy.example.com:8080')

# Proxy rotation (round-robin per request)
yt = YouTube(proxies=[
    'http://user:pass@proxy1:8080',
    'http://user:pass@proxy2:8080',
])

# SOCKS5
yt = YouTube(proxy='socks5://user:pass@proxy:1080')

# Custom timeout and retries
yt = YouTube(proxy='http://proxy:8080', timeout=60.0, max_retries=5)

# Separate proxy pool for transcripts (recommended for mass scraping)
# YouTube's player/caption endpoints are stricter about datacenter IPs.
# Use residential proxies for transcripts, cheaper datacenter proxies for the rest.
yt = YouTube(
    proxies=['http://dc-proxy1:8080', 'http://dc-proxy2:8080'],
    transcript_proxies=['http://residential1:8080', 'http://residential2:8080'],
)
```

> **Tip:** YouTube blocks datacenter IPs aggressively, especially for transcripts. Use rotating residential proxies (BrightData, SmartProxy, Oxylabs) for production. The `transcript_proxy` / `transcript_proxies` parameters let you use residential proxies only where needed.

---

## CLI

Install with `pip install "tubescrape[cli]"`.

![tubescrape search](assets/cli_search.png)
![tubescrape channel search](assets/cli_channel_search.png)
![tubescrape transcript](assets/cli_transcript.png)
![tubescrape transcript srt](assets/cli_transcript_srt.png)

```bash
tubescrape search "python tutorial" -n 5
tubescrape search "podcast" --type video --duration long --sort-by view_count
tubescrape search "python" --json                    # JSON output

tubescrape channel @lexfridman                       # videos (default)
tubescrape channel @lexfridman shorts                # shorts
tubescrape channel @lexfridman playlists             # playlists
tubescrape channel @lexfridman search "podcast"      # search within channel

tubescrape playlist PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf

tubescrape transcript dQw4w9WgXcQ                    # plain text
tubescrape transcript dQw4w9WgXcQ --format srt       # SRT subtitles
tubescrape transcript dQw4w9WgXcQ --translate es      # translate
tubescrape transcript dQw4w9WgXcQ --save output.srt  # save to file
tubescrape transcript dQw4w9WgXcQ --list-languages   # available languages
```

```bash
tubescrape --proxy http://user:pass@host:port search "python"  # with proxy
export TUBESCRAPE_PROXY="http://user:pass@host:port"           # env variable
```

---

## REST API

Install with `pip install "tubescrape[api]"`.

```bash
tubescrape serve                          # starts on localhost:8000
tubescrape serve --host 0.0.0.0 --port 3000
```

Interactive Swagger docs at `http://localhost:8000/docs`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/search?q=python` | Search videos |
| GET | `/api/v1/channel/{id}/videos` | Channel videos |
| GET | `/api/v1/channel/{id}/shorts` | Channel shorts |
| GET | `/api/v1/channel/{id}/playlists` | Channel playlists |
| GET | `/api/v1/channel/{id}/search?q=...` | Search within channel |
| GET | `/api/v1/playlist/{id}` | Fetch playlist |
| GET | `/api/v1/transcript/{video_id}` | Fetch transcript |
| GET | `/api/v1/transcript/{video_id}/languages` | List languages |
| GET | `/health` | Health check |

```bash
curl "http://localhost:8000/api/v1/search?q=python+tutorial&max_results=5"
curl "http://localhost:8000/api/v1/transcript/dQw4w9WgXcQ?format=srt&translate_to=es"
```

---

## Error Handling

All exceptions inherit from `YouTubeError`:

```
YouTubeError
├── RequestError
│   ├── RateLimitError          # HTTP 429, retried automatically
│   ├── ProxyBlockedError       # Proxy firewall block, retried with rotation
│   ├── CaptchaError            # Bot verification challenge, retried with rotation
│   └── BotDetectedError        # HTTP 403
├── VideoUnavailableError       # private, deleted, region-locked
│   └── AgeRestrictedError
├── TranscriptsDisabledError
├── TranscriptsNotAvailableError
├── TranscriptFetchError
├── TranslationNotAvailableError
├── ChannelNotFoundError
├── PlaylistNotFoundError
├── APIKeyNotFoundError
└── ParsingError
```

```python
from tubescrape import YouTube, YouTubeError, RateLimitError, ProxyBlockedError

try:
    results = yt.search('python')
except RateLimitError:
    print('Rate limited, use a proxy')
except ProxyBlockedError:
    print('Proxy blocked by firewall, use residential proxies')
except YouTubeError as e:
    print(f'YouTube error: {e}')
```

---

## Full Documentation

For detailed examples, all field references, and advanced usage, see the **[Complete Usage Guide](docs/guide.md)**.

---

## Warning

This library uses YouTube's undocumented InnerTube API. It may break if YouTube changes their internal API. If it does, please [open an issue](https://github.com/zaidkx37/tubescrape/issues).

---

## Contributing

```bash
git clone https://github.com/zaidkx37/tubescrape.git
cd tubescrape
pip install -e ".[all,dev]"

pytest                    # run tests
ruff check src/           # lint
mypy src/tubescrape/      # type check
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
