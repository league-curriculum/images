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
