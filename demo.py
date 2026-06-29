"""
tubescrape - Demo Script
=========================
Shows actual output from every feature.
Run: python demo.py
"""

import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

import tubescrape

yt = tubescrape.YouTube()


def section(title):
    print(f'\n{"=" * 60}')
    print(f'  {title}')
    print(f'{"=" * 60}\n')


def wait():
    input('\n  Press Enter to continue...\n')


# ─────────────────────────────────────────────────────────────
# 1. VIDEO SEARCH
# ─────────────────────────────────────────────────────────────
section('1. VIDEO SEARCH (query="dog toys", max_results=30)')

result = yt.search('dog toys', max_results=30)
print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
wait()


# ─────────────────────────────────────────────────────────────
# 2. CHANNEL SEARCH
# ─────────────────────────────────────────────────────────────
section('2. CHANNEL SEARCH (query="happy cow", type="channel")')

ch_result = yt.search('happy cow', type='channel', max_results=10)
print(json.dumps(ch_result.to_dict(), indent=2, ensure_ascii=False))
wait()


# ─────────────────────────────────────────────────────────────
# 3. PLAYLIST
# ─────────────────────────────────────────────────────────────
section('3. PLAYLIST (id="PL03F969BA30CE1CE1", max_results=0 / all)')

pl = yt.get_playlist('PL03F969BA30CE1CE1', max_results=0)
print(json.dumps(pl.to_dict(), indent=2, ensure_ascii=False))
wait()


# ─────────────────────────────────────────────────────────────
# 4. CHANNEL VIDEOS
# ─────────────────────────────────────────────────────────────
section('4. CHANNEL VIDEOS (channel="UCOKoxVSOXpz1aQhnGPnSSww", max_results=0 / all)')

browse = yt.get_channel_videos('UCOKoxVSOXpz1aQhnGPnSSww', max_results=0)
print(json.dumps(browse.to_dict(), indent=2, ensure_ascii=False))
wait()


# ─────────────────────────────────────────────────────────────
# 5. VIDEO INFO
# ─────────────────────────────────────────────────────────────
section('5. VIDEO INFO (video="dQw4w9WgXcQ")')

info = yt.get_video_info('dQw4w9WgXcQ')
print(json.dumps(info.to_dict(), indent=2, ensure_ascii=False))
wait()


# ─────────────────────────────────────────────────────────────
# 6. TRANSCRIPT
# ─────────────────────────────────────────────────────────────
section('6. TRANSCRIPT (video="dQw4w9WgXcQ")')

transcript = yt.get_transcript('dQw4w9WgXcQ')
print(json.dumps(transcript.to_dict(), indent=2, ensure_ascii=False))
wait()


# ─────────────────────────────────────────────────────────────
# 7. LIST TRANSCRIPTS
# ─────────────────────────────────────────────────────────────
section('7. LIST TRANSCRIPTS (video="dQw4w9WgXcQ")')

entries = yt.list_transcripts('dQw4w9WgXcQ')
print(json.dumps([e.to_dict() for e in entries], indent=2, ensure_ascii=False))
wait()


# ─────────────────────────────────────────────────────────────
# 8. CHANNEL SHORTS
# ─────────────────────────────────────────────────────────────
section('8. CHANNEL SHORTS (channel="UCX6OQ3DkcsbYNE6H8uQQuVA" / MrBeast)')

shorts = yt.get_channel_shorts('UCX6OQ3DkcsbYNE6H8uQQuVA')
print(json.dumps(shorts.to_dict(), indent=2, ensure_ascii=False))
wait()


# ─────────────────────────────────────────────────────────────
# 9. CHANNEL PLAYLISTS
# ─────────────────────────────────────────────────────────────
section('9. CHANNEL PLAYLISTS (channel="UCOKoxVSOXpz1aQhnGPnSSww")')

ch_playlists = yt.get_channel_playlists('UCOKoxVSOXpz1aQhnGPnSSww')
print(json.dumps(ch_playlists.to_dict(), indent=2, ensure_ascii=False))
wait()


# ─────────────────────────────────────────────────────────────
# 10. SEARCH WITHIN CHANNEL
# ─────────────────────────────────────────────────────────────
section('10. SEARCH WITHIN CHANNEL (channel="UCOKoxVSOXpz1aQhnGPnSSww", query="tetris")')

ch_search = yt.search_channel('UCOKoxVSOXpz1aQhnGPnSSww', 'tetris')
print(json.dumps(ch_search.to_dict(), indent=2, ensure_ascii=False))


yt.close()
print('\nDone.')
