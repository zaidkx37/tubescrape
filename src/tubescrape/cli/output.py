from __future__ import annotations

import json

from tubescrape.models import (
    BrowseResult,
    ChannelPlaylistsResult,
    PlaylistResult,
    SearchResult,
    ShortsResult,
    TranscriptListEntry,
)


def print_search_results(result: SearchResult, output_json: bool = False) -> None:
    """Print search results to terminal."""
    if output_json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return

    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title=f'Search: {result.query}', show_lines=True)
        table.add_column('#', style='dim', width=4)
        table.add_column('Title', style='bold', max_width=50)
        table.add_column('Channel', style='cyan', max_width=25)
        table.add_column('Duration', justify='right')
        table.add_column('Published', style='dim')

        for i, video in enumerate(result.videos, start=1):
            table.add_row(
                str(i),
                video.title,
                video.channel,
                video.duration or '-',
                video.published_text or '-',
            )

        console.print(table)
        console.print('[dim]%d results[/dim]' % len(result.videos))

    except ImportError:
        _print_search_plain(result)


def print_browse_results(result: BrowseResult, output_json: bool = False) -> None:
    """Print channel browse results to terminal."""
    if output_json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return

    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title=f'Channel: {result.channel_id}', show_lines=True)
        table.add_column('#', style='dim', width=4)
        table.add_column('Title', style='bold', max_width=50)
        table.add_column('Duration', justify='right')
        table.add_column('Published', style='dim')

        for i, video in enumerate(result.videos, start=1):
            table.add_row(
                str(i),
                video.title,
                video.duration or '-',
                video.published_text or '-',
            )

        console.print(table)
        console.print('[dim]%d videos[/dim]' % len(result.videos))

    except ImportError:
        _print_browse_plain(result)


def print_transcript_languages(
    entries: list[TranscriptListEntry],
    video_id: str,
    output_json: bool = False,
) -> None:
    """Print available transcript languages."""
    if output_json:
        print(json.dumps(
            [e.to_dict() for e in entries],
            indent=2,
            ensure_ascii=False,
        ))
        return

    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title=f'Transcripts for {video_id}')
        table.add_column('Language', style='bold')
        table.add_column('Code')
        table.add_column('Type')
        table.add_column('Translatable')

        for entry in entries:
            table.add_row(
                entry.language,
                entry.language_code,
                'Auto-generated' if entry.is_generated else 'Manual',
                'Yes' if entry.is_translatable else 'No',
            )

        console.print(table)

    except ImportError:
        for entry in entries:
            kind = 'auto' if entry.is_generated else 'manual'
            print(f'{entry.language} ({entry.language_code}) [{kind}]')


def print_playlist_results(result: PlaylistResult, output_json: bool = False) -> None:
    """Print playlist results to terminal."""
    if output_json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return

    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        title = 'Playlist: %s' % (result.title or result.playlist_id)
        table = Table(title=title, show_lines=True)
        table.add_column('#', style='dim', width=4)
        table.add_column('Title', style='bold', max_width=50)
        table.add_column('Channel', style='cyan', max_width=25)
        table.add_column('Duration', justify='right')

        for i, video in enumerate(result.videos, start=1):
            table.add_row(
                str(i),
                video.title,
                video.channel,
                video.duration or '-',
            )

        console.print(table)
        if result.channel:
            console.print(f'[dim]By: {result.channel}[/dim]')
        console.print('[dim]%d videos[/dim]' % len(result.videos))

    except ImportError:
        _print_playlist_plain(result)


def _print_playlist_plain(result: PlaylistResult) -> None:
    """Fallback plain text output for playlist results."""
    title = result.title or result.playlist_id
    print(f'Playlist: {title}\n')
    if result.channel:
        print(f'By: {result.channel}\n')
    for i, video in enumerate(result.videos, start=1):
        print('%d. %s' % (i, video.title))
        print('   Channel: {} | Duration: {}'.format(
            video.channel, video.duration or '-',
        ))
        print(f'   {video.url}\n')


def print_shorts_results(result: ShortsResult, output_json: bool = False) -> None:
    """Print channel shorts results to terminal."""
    if output_json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return

    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title=f'Shorts: {result.channel_id}', show_lines=True)
        table.add_column('#', style='dim', width=4)
        table.add_column('Title', style='bold', max_width=50)
        table.add_column('Views', justify='right')

        for i, short in enumerate(result.shorts, start=1):
            table.add_row(str(i), short.title, short.view_count or '-')

        console.print(table)
        console.print('[dim]%d shorts[/dim]' % len(result.shorts))

    except ImportError:
        _print_shorts_plain(result)


def print_channel_playlists_results(
    result: ChannelPlaylistsResult, output_json: bool = False,
) -> None:
    """Print channel playlists results to terminal."""
    if output_json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return

    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title=f'Playlists: {result.channel_id}', show_lines=True)
        table.add_column('#', style='dim', width=4)
        table.add_column('Title', style='bold', max_width=50)
        table.add_column('Videos', justify='right')

        for i, pl in enumerate(result.playlists, start=1):
            table.add_row(str(i), pl.title, pl.video_count or '-')

        console.print(table)
        console.print('[dim]%d playlists[/dim]' % len(result.playlists))

    except ImportError:
        _print_channel_playlists_plain(result)


def _print_shorts_plain(result: ShortsResult) -> None:
    """Fallback plain text output for shorts results."""
    print(f'Shorts: {result.channel_id}\n')
    for i, short in enumerate(result.shorts, start=1):
        print('%d. %s' % (i, short.title))
        print('   Views: %s' % (short.view_count or '-'))
        print(f'   {short.url}\n')


def _print_channel_playlists_plain(result: ChannelPlaylistsResult) -> None:
    """Fallback plain text output for channel playlists."""
    print(f'Playlists: {result.channel_id}\n')
    for i, pl in enumerate(result.playlists, start=1):
        print('%d. %s' % (i, pl.title))
        print('   Videos: %s' % (pl.video_count or '-'))
        print(f'   {pl.url}\n')


def _print_search_plain(result: SearchResult) -> None:
    """Fallback plain text output for search results."""
    print(f'Search: {result.query}\n')
    for i, video in enumerate(result.videos, start=1):
        print('%d. %s' % (i, video.title))
        print('   Channel: {} | Duration: {} | {}'.format(
            video.channel, video.duration or '-', video.published_text or '-',
        ))
        print(f'   {video.url}\n')


def _print_browse_plain(result: BrowseResult) -> None:
    """Fallback plain text output for browse results."""
    print(f'Channel: {result.channel_id}\n')
    for i, video in enumerate(result.videos, start=1):
        print('%d. %s' % (i, video.title))
        print('   Duration: {} | {}'.format(video.duration or '-', video.published_text or '-'))
        print(f'   {video.url}\n')
