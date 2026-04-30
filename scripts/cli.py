#!/usr/bin/env python3
"""mkimg CLI - Image catalog management for League images."""

import click
from pathlib import Path

BASE = Path(__file__).parent.parent


@click.group()
def cli():
    """Image catalog management for The League of Amazing Programmers."""
    pass


@cli.command()
@click.argument('categories', nargs=-1)
def describe(categories):
    """Use Claude vision to describe images and write YAML metadata.

    Pass category names to process specific directories, or omit to process all.
    Skips images that already have a .yaml file.
    """
    from scripts.describe import run_describe
    run_describe(BASE, list(categories) if categories else None)


@cli.command()
def compile():
    """Compile all YAML descriptions into a single JSON data file."""
    from scripts.compile import run_compile
    run_compile(BASE)


@cli.command()
def index():
    """Generate HTML index pages from compiled data."""
    from scripts.index import run_index
    run_index(BASE)


@cli.command()
@click.option('--port', default=8000, type=int, help='Port to serve on.')
@click.option('--no-build', is_flag=True, help='Skip the compile + index rebuild.')
@click.option('--no-open', is_flag=True, help="Don't open the browser.")
def serve(port, no_build, no_open):
    """Build the site and serve it locally for previewing.

    Runs compile + index (use --no-build to skip), then serves from the
    repo root so the relative ../<category>/<file> image paths resolve.
    Opens the browser to the catalog index.
    """
    import functools
    import http.server
    import socketserver
    import threading
    import webbrowser

    if not no_build:
        from scripts.compile import run_compile
        from scripts.index import run_index
        click.echo("=== Compile ===")
        run_compile(BASE)
        click.echo("\n=== Index ===")
        run_index(BASE)
        click.echo("")

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(BASE))
    socketserver.TCPServer.allow_reuse_address = True
    url = f"http://localhost:{port}/_site/"

    with socketserver.TCPServer(("", port), handler) as httpd:
        click.echo(f"Serving {BASE} at {url}")
        click.echo("Press Ctrl-C to stop.")
        if not no_open:
            threading.Timer(0.4, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            click.echo("\nStopped.")


@cli.command()
@click.option('--dry-run', is_flag=True, help='List what would be uploaded without touching MediaCMS.')
@click.option('--category', 'categories', multiple=True, help='Restrict to one or more categories.')
@click.option('--exclude', 'exclude', multiple=True, help='Skip one or more categories.')
@click.option('--limit', type=int, default=0, help='Stop after uploading this many new images (0 = no limit).')
def upload(dry_run, categories, exclude, limit):
    """Import all images and metadata into MediaCMS.

    Reads MEDIACMS_API and MEDIACMS_API_TOKEN from .env. Categories must
    already exist on the server (create via admin); tags are auto-created
    when assigned. State is tracked in data/mediacms_state.json so re-runs
    skip already-uploaded images.
    """
    from scripts.upload import run_upload
    run_upload(BASE, dry_run=dry_run,
               only_categories=list(categories) if categories else None,
               exclude_categories=list(exclude) if exclude else None,
               limit=limit)


@cli.command()
def build():
    """Run full pipeline: describe, compile, index.

    The describe step requires ANTHROPIC_API_KEY. If the key is not set,
    describe is skipped and the build continues with compile and index
    using existing YAML files.
    """
    from scripts.describe import run_describe
    from scripts.compile import run_compile
    from scripts.index import run_index

    click.echo("=== Step 1: Describe ===")
    run_describe(BASE, None)
    click.echo("\n=== Step 2: Compile ===")
    run_compile(BASE)
    click.echo("\n=== Step 3: Index ===")
    run_index(BASE)
    click.echo("\nBuild complete!")


def main():
    cli()


if __name__ == '__main__':
    main()
