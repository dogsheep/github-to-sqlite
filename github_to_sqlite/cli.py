import click
import datetime
import pathlib
import os
import sqlite_utils
import time
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
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=True),
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
    repo_full = utils.fetch_repo(repo, token)
    if load:
        issues = json.load(open(load))
    else:
        issues = utils.fetch_issues(repo, token, issue)

    issues = list(issues)
    utils.save_issues(db, issues, repo_full)
    utils.ensure_db_shape(db)


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
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=True),
    default="auth.json",
    help="Path to auth.json token file",
)
def issue_comments(db_path, repo, issue, auth):
    "Retrieve issue comments for a specific repository"
    db = sqlite_utils.Database(db_path)
    token = load_token(auth)
    for comment in utils.fetch_issue_comments(repo, token, issue):
        utils.save_issue_comment(db, comment)
    utils.ensure_db_shape(db)


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
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=True),
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
    utils.ensure_db_shape(db)


@cli.command()
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    required=True,
)
@click.argument("repos", type=str, nargs=-1)
@click.option(
    "-a",
    "--auth",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=True, exists=True),
    default="auth.json",
    help="Path to auth.json token file",
)
def stargazers(db_path, repos, auth):
    "Fetch the users that have starred the specified repositories"
    db = sqlite_utils.Database(db_path)
    token = load_token(auth)
    for repo in repos:
        full_repo = utils.fetch_repo(repo, token=token)
        repo_id = utils.save_repo(db, full_repo)
        stargazers = utils.fetch_stargazers(repo, token)
        utils.save_stargazers(db, repo_id, stargazers)
    utils.ensure_db_shape(db)


@cli.command()
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    required=True,
)
@click.argument("usernames", type=str, nargs=-1)
@click.option(
    "-a",
    "--auth",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=True),
    default="auth.json",
    help="Path to auth.json token file",
)
@click.option(
    "-r",
    "--repo",
    multiple=True,
    help="Just fetch these repos",
)
@click.option(
    "--load",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=True, exists=True),
    help="Load issues JSON from this file instead of the API",
)
def repos(db_path, usernames, auth, repo, load):
    "Save repos owened by the specified (or authenticated) username or organization"
    db = sqlite_utils.Database(db_path)
    token = load_token(auth)
    if load:
        for loaded_repo in json.load(open(load)):
            utils.save_repo(db, loaded_repo)
    else:
        if repo:
            # Just these repos
            for full_name in repo:
                utils.save_repo(db, utils.fetch_repo(full_name, token))
        else:
            if not usernames:
                usernames = [None]
            for username in usernames:
                for repo in utils.fetch_all_repos(username, token):
                    utils.save_repo(db, repo)
    utils.ensure_db_shape(db)


@cli.command()
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    required=True,
)
@click.argument("repos", type=str, nargs=-1)
@click.option(
    "-a",
    "--auth",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=True),
    default="auth.json",
    help="Path to auth.json token file",
)
def releases(db_path, repos, auth):
    "Save releases for the specified repos"
    db = sqlite_utils.Database(db_path)
    token = load_token(auth)
    for repo in repos:
        repo_full = utils.fetch_repo(repo, token)
        utils.save_repo(db, repo_full)
        releases = utils.fetch_releases(repo, token)
        utils.save_releases(db, releases, repo_full["id"])
        time.sleep(1)
    utils.ensure_db_shape(db)


@cli.command()
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    required=True,
)
@click.argument("repos", type=str, nargs=-1)
@click.option(
    "-a",
    "--auth",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=True),
    default="auth.json",
    help="Path to auth.json token file",
)
def contributors(db_path, repos, auth):
    "Save contributors for the specified repos"
    db = sqlite_utils.Database(db_path)
    token = load_token(auth)
    for repo in repos:
        repo_full = utils.fetch_repo(repo, token)
        utils.save_repo(db, repo_full)
        contributors = utils.fetch_contributors(repo, token)
        utils.save_contributors(db, contributors, repo_full["id"])
        time.sleep(1)
    utils.ensure_db_shape(db)


@cli.command()
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    required=True,
)
@click.argument("repos", type=str, nargs=-1)
@click.option(
    "--all",
    is_flag=True,
    default=False,
    help="Load all commits (not just those that have not yet been saved)",
)
@click.option(
    "-a",
    "--auth",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=True),
    default="auth.json",
    help="Path to auth.json token file",
)
def commits(db_path, repos, all, auth):
    "Save commits for the specified repos"
    db = sqlite_utils.Database(db_path)
    token = load_token(auth)

    def stop_when(commit):
        try:
            db["commits"].get(commit["sha"])
            return True
        except sqlite_utils.db.NotFoundError:
            return False

    if all:
        stop_when = None

    for repo in repos:
        repo_full = utils.fetch_repo(repo, token)
        utils.save_repo(db, repo_full)

        commits = utils.fetch_commits(repo, token, stop_when)
        utils.save_commits(db, commits, repo_full["id"])
        time.sleep(1)

    utils.ensure_db_shape(db)


@cli.command(name="scrape-dependents")
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    required=True,
)
@click.argument("repos", type=str, nargs=-1)
@click.option(
    "-a",
    "--auth",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=True),
    default="auth.json",
    help="Path to auth.json token file",
)
@click.option(
    "-v", "--verbose", is_flag=True, help="Verbose output",
)
def scrape_dependents(db_path, repos, auth, verbose):
    "Scrape dependents for specified repos"
    try:
        import bs4
    except ImportError:
        raise click.ClickException("Optional dependency bs4 is needed for this command")
    db = sqlite_utils.Database(db_path)
    token = load_token(auth)

    for repo in repos:
        repo_full = utils.fetch_repo(repo, token)
        utils.save_repo(db, repo_full)

        for dependent_repo in utils.scrape_dependents(repo, verbose):
            # Don't fetch repo details if it's already in our DB
            existing = list(db["repos"].rows_where("full_name = ?", [dependent_repo]))
            dependent_id = None
            if not existing:
                dependent_full = utils.fetch_repo(dependent_repo, token)
                time.sleep(1)
                utils.save_repo(db, dependent_full)
                dependent_id = dependent_full["id"]
            else:
                dependent_id = existing[0]["id"]
            # Only insert if it isn't already there:
            if not db["dependents"].exists() or not list(
                db["dependents"].rows_where(
                    "repo = ? and dependent = ?", [repo_full["id"], dependent_id]
                )
            ):
                db["dependents"].insert(
                    {
                        "repo": repo_full["id"],
                        "dependent": dependent_id,
                        "first_seen_utc": datetime.datetime.utcnow().isoformat(),
                    },
                    pk=("repo", "dependent"),
                    foreign_keys=(
                        ("repo", "repos", "id"),
                        ("dependent", "repos", "id"),
                    ),
                )

    utils.ensure_db_shape(db)


def load_token(auth):
    try:
        token = json.load(open(auth))["github_personal_token"]
    except (KeyError, FileNotFoundError):
        token = None
    if token is None:
        # Fallback to GITHUB_TOKEN environment variable
        token = os.environ.get("GITHUB_TOKEN") or None
    return token
