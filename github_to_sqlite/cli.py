import click
import pathlib
import os
import sqlite_utils
import json
from github_to_sqlite import utils


@click.group()
@click.version_option()
def cli():
    "Save data from GitHub to a SQLite database"


@cli.command()
@click.option(
    "-a",
    "--auth",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    default="auth.json",
    help="Path to save tokens to, defaults to auth.json",
)
def auth(auth):
    "Save authentication credentials to a JSON file"
    click.echo("Create a GitHub personal user token and paste it here:")
    click.echo()
    personal_token = click.prompt("Personal token")
    if pathlib.Path(auth).exists():
        auth_data = json.load(open(auth))
    else:
        auth_data = {}
    auth_data["github_personal_token"] = personal_token
    open(auth, "w").write(json.dumps(auth_data, indent=4) + "\n")


@cli.command()
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    required=True,
)
@click.argument("repo", required=False)
@click.option(
    "-a",
    "--auth",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=True, exists=True),
    default="auth.json",
    help="Path to auth.json token file",
)
@click.option(
    "--load",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=True, exists=True),
    help="Load issues JSON from this file instead of the API",
)
def issues(db_path, repo, auth, load):
    "Save issues for a specified repository, e.g. simonw/datasette"
    db = sqlite_utils.Database(db_path)
    if load:
        issues = json.load(open(load))
    try:
        token = json.load(open(auth))["github_personal_token"]
    except (KeyError, FileNotFoundError):
        token = None

    utils.save_issues(db, utils.fetch_all_issues(repo, token))
