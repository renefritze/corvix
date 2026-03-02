"""Console script for corvix."""

import sys

import click


@click.command()
def main(args: list[str] | None = None) -> int:
    """Console script for corvix."""
    click.echo("Replace this message by putting your code into corvix.cli.main")
    click.echo("See click documentation at https://click.palletsprojects.com/")
    print(f"Gotta use the args: {args}")
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
