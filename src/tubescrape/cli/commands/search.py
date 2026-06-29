from __future__ import annotations

import click

from tubescrape.cli.output import print_search_results


@click.command()
@click.argument('query')
@click.option('--max-results', '-n', default=20, type=int,
              help='Maximum results (0 for all).')
@click.option('--type', '-t', 'content_type', default=None,
              type=click.Choice(['video', 'channel', 'playlist', 'movie'], case_sensitive=False),
              help='Content type filter.')
@click.option('--duration', '-d', default=None,
              type=click.Choice(['short', 'medium', 'long'], case_sensitive=False),
              help='Duration filter: short (<4min), medium (4-20min), long (>20min).')
@click.option('--upload-date', '-u', default=None,
              type=click.Choice(['last_hour', 'today', 'this_week', 'this_month', 'this_year'],
                                case_sensitive=False),
              help='Upload date filter.')
@click.option('--sort-by', '-s', default=None,
              type=click.Choice(['relevance', 'upload_date', 'view_count', 'rating'],
                                case_sensitive=False),
              help='Sort order.')
@click.option('--features', '-f', multiple=True,
              help='Feature filter(s): live, 4k, hd, subtitles, cc, hdr, etc.')
@click.option('--params', '-p', default='', help='Raw protobuf-encoded search filter (base64).')
@click.option('--json', 'output_json', is_flag=True, help='Output as JSON.')
@click.pass_context
def search(
    ctx: click.Context,
    query: str,
    max_results: int,
    content_type: str | None,
    duration: str | None,
    upload_date: str | None,
    sort_by: str | None,
    features: tuple[str, ...],
    params: str,
    output_json: bool,
) -> None:
    """Search YouTube videos.

    \b
    Examples:
        tubescrape search "python tutorial"
        tubescrape search "machine learning" -n 10
        tubescrape search "podcast" --type video --duration long
        tubescrape search "news" --upload-date today --sort-by view_count
        tubescrape search "music" --features 4k --features hdr
        tubescrape search "podcast" --json
    """
    from tubescrape import YouTube

    proxy = ctx.obj.get('proxy')
    yt = YouTube(proxy=proxy)

    try:
        result = yt.search(
            query,
            max_results=max_results,
            params=params,
            sort_by=sort_by,
            upload_date=upload_date,
            type=content_type,
            duration=duration,
            features=list(features) if features else None,
        )
        print_search_results(result, output_json=output_json)
    finally:
        yt.close()
