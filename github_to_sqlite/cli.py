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
@click.option("--issue", help="Just pull this issue number")
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
def issues(db_path, repo, issue, auth, load):
    "Save issues for a specified repository, e.g. simonw/datasette"
    db = sqlite_utils.Database(db_path)
    token = load_token(auth)
    if load:
        issues = json.load(open(load))
    else:
        issues = utils.fetch_issues(repo, token, issue)

    issues = list(issues)
    utils.save_issues(db, issues)


@cli.command(name="issue-comments")
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    required=True,
)
@click.argument("repo")
@click.option("--issue", help="Just pull comments for this issue")
@click.option(
    "-a",
    "--auth",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=True, exists=True),
    default="auth.json",
    help="Path to auth.json token file",
)
def issue_comments(db_path, repo, issue, auth):
    "Retrieve issue comments for a specific repository"
    db = sqlite_utils.Database(db_path)
    token = load_token(auth)
    for comment in utils.fetch_issue_comments(repo, token, issue):
        utils.save_issue_comment(db, comment)


@cli.command()
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    required=True,
)
@click.argument("username", type=str, required=False)
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
def starred(db_path, username, auth, load):
    "Save repos starred by the specified (or authenticated) username"
    db = sqlite_utils.Database(db_path)
    token = load_token(auth)
    if load:
        stars = json.load(open(load))
    else:
        stars = utils.fetch_all_starred(username, token)

    # Which user are we talking about here?
    if username:
        user = utils.fetch_user(username, token)
    else:
        user = utils.fetch_user(token=token)

    utils.save_stars(db, user, stars)
    utils.ensure_repo_fts(db)
    utils.ensure_foreign_keys(db)


@cli.command()
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    required=True,
)
@click.argument("identifiers", type=str, nargs=-1)
@click.option(
    "--attach",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False, exists=True),
    multiple=True,
    help="Additional database file to attach",
)
@click.option("--sql", help="SQL query to fetch identifiers to use")
@click.option("--ids", is_flag=True, default=False)
@click.option(
    "-a",
    "--auth",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=True, exists=True),
    default="auth.json",
    help="Path to auth.json token file",
)
@click.option("--sql", type=str)
def stargazers(db_path, identifiers, attach, sql, ids, auth):
    "Fetch the users that have starred the specified repositories"
    db = sqlite_utils.Database(db_path)
    identifiers = utils.resolve_identifiers(db, identifiers, attach, sql)
    token = load_token(auth)
    for identifier in identifiers:
        repo = utils.fetch_repo(identifier, token, ids)
        repo_id = utils.save_repo(db, repo)
        stargazers = utils.fetch_stargazers(identifier, token, ids)
        utils.save_stargazers(db, repo_id, stargazers)
    utils.ensure_repo_fts(db)
    utils.ensure_foreign_keys(db)


@cli.command()
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    required=True,
)
@click.argument("username", type=str, required=False)
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
def repos(db_path, username, auth, load):
    "Save repos owened by the specified (or authenticated) username or organization"
    db = sqlite_utils.Database(db_path)
    token = load_token(auth)
    if load:
        repos = json.load(open(load))
    else:
        repos = utils.fetch_all_repos(username, token)

    # Which user are we talking about here?
    user = utils.fetch_user(username=username, token=token)
    for repo in repos:
        utils.save_repo(db, repo)
    utils.ensure_repo_fts(db)
    utils.ensure_foreign_keys(db)


def load_token(auth):
    try:
        token = json.load(open(auth))["github_personal_token"]
    except (KeyError, FileNotFoundError):
        token = None
    return token
