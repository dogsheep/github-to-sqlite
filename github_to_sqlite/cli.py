import click
import datetime
import pathlib
import textwrap
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
@click.argument("repo")
@click.option(
    "--issue",
    "issue_ids",
    help="Just pull these issue numbers",
    type=int,
    multiple=True,
)
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
def issues(db_path, repo, issue_ids, auth, load):
    "Save issues for a specified repository, e.g. simonw/datasette"
    db = sqlite_utils.Database(db_path)
    token = load_token(auth)
    repo_full = utils.fetch_repo(repo, token)
    utils.save_repo(db, repo_full)
    if load:
        issues = json.load(open(load))
    else:
        issues = utils.fetch_issues(repo, token, issue_ids)

    issues = list(issues)
    utils.save_issues(db, issues, repo_full)
    utils.ensure_db_shape(db)


@cli.command(name="pull-requests")
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    required=True,
)
@click.argument("repo", required=False)
@click.option(
    "--pull-request",
    "pull_request_ids",
    help="Just pull these pull-request numbers",
    type=int,
    multiple=True,
)
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
    help="Load pull-requests JSON from this file instead of the API",
)
def pull_requests(db_path, repo, pull_request_ids, auth, load):
    "Save pull_requests for a specified repository, e.g. simonw/datasette"
    db = sqlite_utils.Database(db_path)
    token = load_token(auth)
    repo_full = utils.fetch_repo(repo, token)
    utils.save_repo(db, repo_full)
    if load:
        pull_requests = json.load(open(load))
    else:
        pull_requests = utils.fetch_pull_requests(repo, token, pull_request_ids)

    pull_requests = list(pull_requests)
    utils.save_pull_requests(db, pull_requests, repo_full)
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
    help="Load repos JSON from this file instead of the API",
)
@click.option(
    "--readme",
    is_flag=True,
    help="Fetch README into 'readme' column",
)
@click.option(
    "--readme-html",
    is_flag=True,
    help="Fetch HTML rendered README into 'readme_html' column",
)
def repos(db_path, usernames, auth, repo, load, readme, readme_html):
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
                repo_id = utils.save_repo(db, utils.fetch_repo(full_name, token))
                _repo_readme(db, token, repo_id, full_name, readme, readme_html)
        else:
            if not usernames:
                usernames = [None]
            for username in usernames:
                for repo in utils.fetch_all_repos(username, token):
                    repo_id = utils.save_repo(db, repo)
                    _repo_readme(
                        db, token, repo_id, repo["full_name"], readme, readme_html
                    )
    utils.ensure_db_shape(db)


def _repo_readme(db, token, repo_id, full_name, readme, readme_html):
    if readme:
        readme = utils.fetch_readme(token, full_name)
        db["repos"].update(repo_id, {"readme": readme}, alter=True)
    if readme_html:
        readme_html = utils.fetch_readme(token, full_name, html=True)
        db["repos"].update(repo_id, {"readme_html": readme_html}, alter=True)


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
    first = True
    for repo in repos:
        if not first:
            time.sleep(1)
        first = False
        repo_full = utils.fetch_repo(repo, token)
        utils.save_repo(db, repo_full)
        releases = utils.fetch_releases(repo, token)
        utils.save_releases(db, releases, repo_full["id"])
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
def tags(db_path, repos, auth):
    "Save tags for the specified repos"
    db = sqlite_utils.Database(db_path)
    token = load_token(auth)
    first = True
    for repo in repos:
        if not first:
            time.sleep(1)
        first = False
        repo_full = utils.fetch_repo(repo, token)
        utils.save_repo(db, repo_full)
        tags = utils.fetch_tags(repo, token)
        utils.save_tags(db, tags, repo_full["id"])
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
    "-v",
    "--verbose",
    is_flag=True,
    help="Verbose output",
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


@cli.command()
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    required=True,
)
@click.option(
    "-a",
    "--auth",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=True),
    default="auth.json",
    help="Path to auth.json token file",
)
@click.option(
    "-f",
    "--fetch",
    is_flag=True,
    help="Fetch the image data into a BLOB column",
)
def emojis(db_path, auth, fetch):
    "Fetch GitHub supported emojis"
    db = sqlite_utils.Database(db_path)
    token = load_token(auth)
    table = db.table("emojis", pk="name")
    table.upsert_all(utils.fetch_emojis(token))
    if fetch:
        # Ensure table has 'image' column
        if "image" not in table.columns_dict:
            table.add_column("image", bytes)
        with click.progressbar(
            list(table.rows_where("image is null")),
            show_pos=True,
            show_eta=True,
            show_percent=True,
        ) as bar:
            for emoji in bar:
                table.update(emoji["name"], {"image": utils.fetch_image(emoji["url"])})


@cli.command()
@click.argument("url", type=str)
@click.option(
    "-a",
    "--auth",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=True),
    default="auth.json",
    help="Path to auth.json token file",
)
@click.option(
    "--paginate",
    is_flag=True,
    help="Paginate through all results",
)
@click.option(
    "--nl",
    is_flag=True,
    help="Output newline-delimited JSON",
)
@click.option(
    "--accept",
    help="Accept header to send, e.g. application/vnd.github.VERSION.html",
)
def get(url, auth, paginate, nl, accept):
    "Save repos owened by the specified (or authenticated) username or organization"
    token = load_token(auth)
    first = True
    should_output_closing_brace = not nl
    while url:
        response = utils.get(url, token, accept=accept)
        if "html" in (response.headers.get("content-type") or ""):
            click.echo(response.text)
            return
        items = response.json()
        if isinstance(items, dict):
            if nl:
                click.echo(json.dumps(items))
            else:
                click.echo(json.dumps(items, indent=4))
            should_output_closing_brace = False
            break
        if first and not nl:
            click.echo("[")
        for item in items:
            if not first and not nl:
                click.echo(",")
            first = False
            if not nl:
                to_dump = json.dumps(item, indent=4)
                click.echo(textwrap.indent(to_dump, "    "), nl=False)
            else:
                click.echo(json.dumps(item))
        if paginate:
            url = response.links.get("next", {}).get("url")
        else:
            url = None
    if should_output_closing_brace:
        click.echo("\n]")


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
def workflows(db_path, repos, auth):
    "Fetch details of GitHub Actions workflows for the specified repositories"
    db = sqlite_utils.Database(db_path)
    token = load_token(auth)
    for repo in repos:
        full_repo = utils.fetch_repo(repo, token=token)
        repo_id = utils.save_repo(db, full_repo)
        workflows = utils.fetch_workflows(token, full_repo["full_name"])
        for filename, content in workflows.items():
            utils.save_workflow(db, repo_id, filename, content)
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
