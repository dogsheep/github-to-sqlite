import base64
import requests
import time
import yaml

FTS_CONFIG = {
    # table: columns
    "commits": ["message"],
    "issue_comments": ["body"],
    "issues": ["title", "body"],
    "pull_requests": ["title", "body"],
    "labels": ["name", "description"],
    "licenses": ["name"],
    "milestones": ["title", "description"],
    "releases": ["name", "body"],
    "repos": ["name", "description"],
    "users": ["login", "name"],
}

VIEWS = {
    # Name: (required_tables, SQL)
    "dependent_repos": (
        {"repos", "dependents"},
        """select
  repos.full_name as repo,
  'https://github.com/' || dependent_repos.full_name as dependent,
  dependent_repos.created_at as dependent_created,
  dependent_repos.updated_at as dependent_updated,
  dependent_repos.stargazers_count as dependent_stars,
  dependent_repos.watchers_count as dependent_watchers
from
  dependents
  join repos as dependent_repos on dependents.dependent = dependent_repos.id
  join repos on dependents.repo = repos.id
order by
  dependent_repos.created_at desc""",
    ),
    "repos_starred": (
        {"stars", "repos", "users"},
        """select
  stars.starred_at,
  starring_user.login as starred_by,
  repos.*
from
  repos
  join stars on repos.id = stars.repo
  join users as starring_user on stars.user = starring_user.id
  join users on repos.owner = users.id
order by
  starred_at desc""",
    ),
    "recent_releases": (
        {"repos", "releases"},
        """select
  repos.rowid as rowid,
  repos.html_url as repo,
  releases.html_url as release,
  substr(releases.published_at, 0, 11) as date,
  releases.body as body_markdown,
  releases.published_at,
  coalesce(repos.topics, '[]') as topics
from
  releases
  join repos on repos.id = releases.repo
order by
  releases.published_at desc""",
    ),
}

FOREIGN_KEYS = [
    ("repos", "license", "licenses", "key"),
]


class GitHubError(Exception):
    def __init__(self, message, status_code):
        self.message = message
        self.status_code = status_code

    @classmethod
    def from_response(cls, response):
        message = response.json()["message"]
        if "git repository is empty" in message.lower():
            cls = GitHubRepositoryEmpty
        return cls(message, response.status_code)


class GitHubRepositoryEmpty(GitHubError):
    pass


def save_issues(db, issues, repo):
    if "milestones" not in db.table_names():
        if "users" not in db.table_names():
            # So we can define the foreign key from milestones:
            db["users"].create({"id": int}, pk="id")
        db["milestones"].create(
            {"id": int, "title": str, "description": str, "creator": int, "repo": int},
            pk="id",
            foreign_keys=(("repo", "repos", "id"), ("creator", "users", "id")),
        )
    for original in issues:
        # Ignore all of the _url fields
        issue = {
            key: value for key, value in original.items() if not key.endswith("url")
        }
        # Add repo key
        issue["repo"] = repo["id"]
        # Pull request can be flattened to just their URL
        if issue.get("pull_request"):
            issue["pull_request"] = issue["pull_request"]["url"].split(
                "https://api.github.com/repos/"
            )[1]
        # Extract user
        issue["user"] = save_user(db, issue["user"])
        labels = issue.pop("labels")
        # Extract milestone
        if issue["milestone"]:
            issue["milestone"] = save_milestone(db, issue["milestone"], repo["id"])
        # For the moment we ignore the assignees=[] array but we DO turn assignee
        # singular into a foreign key reference
        issue.pop("assignees", None)
        if issue["assignee"]:
            issue["assignee"] = save_user(db, issue["assignee"])
        # Add a type field to distinguish issues from pulls
        issue["type"] = "pull" if issue.get("pull_request") else "issue"
        # Insert record
        table = db["issues"].insert(
            issue,
            pk="id",
            foreign_keys=[
                ("user", "users", "id"),
                ("assignee", "users", "id"),
                ("milestone", "milestones", "id"),
                ("repo", "repos", "id"),
            ],
            alter=True,
            replace=True,
            columns={
                "user": int,
                "assignee": int,
                "milestone": int,
                "repo": int,
                "title": str,
                "body": str,
            },
        )
        # m2m for labels
        for label in labels:
            table.m2m("labels", label, pk="id")


def save_pull_requests(db, pull_requests, repo):
    if "milestones" not in db.table_names():
        if "users" not in db.table_names():
            # So we can define the foreign key from milestones:
            db["users"].create({"id": int}, pk="id")
        db["milestones"].create(
            {"id": int, "title": str, "description": str, "creator": int, "repo": int},
            pk="id",
            foreign_keys=(("repo", "repos", "id"), ("creator", "users", "id")),
        )
    for original in pull_requests:
        # Ignore all of the _url fields
        pull_request = {
            key: value for key, value in original.items() if not key.endswith("url")
        }
        # Add repo key
        pull_request["repo"] = repo["id"]
        # Pull request _links can be flattened to just their URL
        pull_request["url"] = pull_request["_links"]["html"]["href"]
        pull_request.pop("_links")
        # Extract user
        pull_request["user"] = save_user(db, pull_request["user"])
        labels = pull_request.pop("labels")
        # Extract merged_by, if it exists
        if pull_request.get("merged_by"):
            pull_request["merged_by"] = save_user(db, pull_request["merged_by"])
        # Head sha
        pull_request["head"] = pull_request["head"]["sha"]
        pull_request["base"] = pull_request["base"]["sha"]
        # Extract milestone
        if pull_request["milestone"]:
            pull_request["milestone"] = save_milestone(
                db, pull_request["milestone"], repo["id"]
            )
        # For the moment we ignore the assignees=[] array but we DO turn assignee
        # singular into a foreign key reference
        pull_request.pop("assignees", None)
        if original["assignee"]:
            pull_request["assignee"] = save_user(db, pull_request["assignee"])
        pull_request.pop("active_lock_reason")
        # ignore requested_reviewers and requested_teams
        pull_request.pop("requested_reviewers", None)
        pull_request.pop("requested_teams", None)
        # Insert record
        table = db["pull_requests"].insert(
            pull_request,
            pk="id",
            foreign_keys=[
                ("user", "users", "id"),
                ("merged_by", "users", "id"),
                ("assignee", "users", "id"),
                ("milestone", "milestones", "id"),
                ("repo", "repos", "id"),
            ],
            alter=True,
            replace=True,
            columns={
                "user": int,
                "assignee": int,
                "milestone": int,
                "repo": int,
                "title": str,
                "body": str,
                "merged_by": int,
            },
        )
        # m2m for labels
        for label in labels:
            table.m2m("labels", label, pk="id")


def save_user(db, user):
    # Remove all url fields except avatar_url and html_url
    to_save = {
        key: value
        for key, value in user.items()
        if (key in ("avatar_url", "html_url") or not key.endswith("url"))
    }
    # If this user was nested in repo they will be missing several fields
    # so fill in 'name' from 'login' so Datasette foreign keys display
    if to_save.get("name") is None:
        to_save["name"] = to_save["login"]
    return db["users"].upsert(to_save, pk="id", alter=True).last_pk


def save_milestone(db, milestone, repo_id):
    milestone = dict(milestone)
    milestone["creator"] = save_user(db, milestone["creator"])
    milestone["repo"] = repo_id
    milestone.pop("labels_url", None)
    milestone.pop("url", None)
    return (
        db["milestones"]
        .insert(
            milestone,
            pk="id",
            foreign_keys=[("creator", "users", "id"), ("repo", "repos", "id")],
            alter=True,
            replace=True,
            columns={"creator": int, "repo": int},
        )
        .last_pk
    )


def save_issue_comment(db, comment):
    comment = dict(comment)
    comment["user"] = save_user(db, comment["user"])
    # We set up a 'issue' foreign key, but only if issue is in the DB
    comment["issue"] = None
    issue_url = comment["issue_url"]
    bits = issue_url.split("/")
    user_slug, repo_slug, issue_number = bits[-4], bits[-3], bits[-1]
    # Is the issue in the DB already?
    issue_rows = list(
        db["issues"].rows_where(
            "number = :number and repo = (select id from repos where full_name = :repo)",
            {"repo": "{}/{}".format(user_slug, repo_slug), "number": issue_number},
        )
    )
    if len(issue_rows) == 1:
        comment["issue"] = issue_rows[0]["id"]
    comment.pop("url", None)
    if "url" in comment.get("reactions", {}):
        comment["reactions"].pop("url")
    last_pk = (
        db["issue_comments"]
        .insert(
            comment, pk="id", foreign_keys=("user", "issue"), alter=True, replace=True
        )
        .last_pk
    )
    return last_pk


def fetch_repo(full_name, token=None):
    headers = make_headers(token)
    # Get topics:
    headers["Accept"] = "application/vnd.github.mercy-preview+json"
    owner, slug = full_name.split("/")
    url = "https://api.github.com/repos/{}/{}".format(owner, slug)
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def save_repo(db, repo):
    assert isinstance(repo, dict), "Repo should be a dict: {}".format(repr(repo))
    # Remove all url fields except html_url
    to_save = {
        key: value
        for key, value in repo.items()
        if (key == "html_url") or not key.endswith("url")
    }
    to_save["owner"] = save_user(db, to_save["owner"])
    to_save["license"] = save_license(db, to_save["license"])
    if "organization" in to_save:
        to_save["organization"] = save_user(db, to_save["organization"])
    else:
        to_save["organization"] = None
    repo_id = (
        db["repos"]
        .insert(
            to_save,
            pk="id",
            foreign_keys=(("owner", "users", "id"), ("organization", "users", "id")),
            alter=True,
            replace=True,
            columns={
                "organization": int,
                "topics": str,
                "name": str,
                "description": str,
            },
        )
        .last_pk
    )
    return repo_id


def save_license(db, license):
    if license is None:
        return None
    return db["licenses"].insert(license, pk="key", replace=True).last_pk


def fetch_issues(repo, token=None, issue_ids=None):
    headers = make_headers(token)
    headers["accept"] = "application/vnd.github.v3+json"
    if issue_ids:
        for issue_id in issue_ids:
            url = "https://api.github.com/repos/{}/issues/{}".format(repo, issue_id)
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            yield response.json()
    else:
        url = "https://api.github.com/repos/{}/issues?state=all&filter=all".format(repo)
        for issues in paginate(url, headers):
            yield from issues


def fetch_pull_requests(repo, token=None, pull_request_ids=None):
    headers = make_headers(token)
    headers["accept"] = "application/vnd.github.v3+json"
    if pull_request_ids:
        for pull_request_id in pull_request_ids:
            url = "https://api.github.com/repos/{}/pulls/{}".format(
                repo, pull_request_id
            )
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            yield response.json()
    else:
        url = "https://api.github.com/repos/{}/pulls?state=all&filter=all".format(repo)
        for pull_requests in paginate(url, headers):
            yield from pull_requests


def fetch_issue_comments(repo, token=None, issue=None):
    assert "/" in repo
    headers = make_headers(token)
    # Get reactions:
    headers["Accept"] = "application/vnd.github.squirrel-girl-preview"
    path = "/repos/{}/issues/comments".format(repo)
    if issue is not None:
        path = "/repos/{}/issues/{}/comments".format(repo, issue)
    url = "https://api.github.com{}".format(path)
    for comments in paginate(url, headers):
        yield from comments


def fetch_releases(repo, token=None):
    headers = make_headers(token)
    url = "https://api.github.com/repos/{}/releases".format(repo)
    for releases in paginate(url, headers):
        yield from releases


def fetch_contributors(repo, token=None):
    headers = make_headers(token)
    url = "https://api.github.com/repos/{}/contributors".format(repo)
    for contributors in paginate(url, headers):
        yield from contributors


def fetch_tags(repo, token=None):
    headers = make_headers(token)
    url = "https://api.github.com/repos/{}/tags".format(repo)
    for tags in paginate(url, headers):
        yield from tags


def fetch_commits(repo, token=None, stop_when=None):
    if stop_when is None:
        stop_when = lambda commit: False
    headers = make_headers(token)
    url = "https://api.github.com/repos/{}/commits".format(repo)
    try:
        for commits in paginate(url, headers):
            for commit in commits:
                if stop_when(commit):
                    return
                else:
                    yield commit
    except GitHubRepositoryEmpty:
        return


def fetch_all_starred(username=None, token=None):
    assert username or token, "Must provide username= or token= or both"
    headers = make_headers(token)
    headers["Accept"] = "application/vnd.github.v3.star+json"
    if username:
        url = "https://api.github.com/users/{}/starred".format(username)
    else:
        url = "https://api.github.com/user/starred"
    for stars in paginate(url, headers):
        yield from stars


def fetch_stargazers(repo, token=None):
    headers = make_headers(token)
    headers["Accept"] = "application/vnd.github.v3.star+json"
    url = "https://api.github.com/repos/{}/stargazers".format(repo)
    for stargazers in paginate(url, headers):
        yield from stargazers


def fetch_all_repos(username=None, token=None):
    assert username or token, "Must provide username= or token= or both"
    headers = make_headers(token)
    # Get topics for each repo:
    headers["Accept"] = "application/vnd.github.mercy-preview+json"
    if username:
        url = "https://api.github.com/users/{}/repos".format(username)
    else:
        url = "https://api.github.com/user/repos"
    for repos in paginate(url, headers):
        yield from repos


def fetch_user(username=None, token=None):
    assert username or token, "Must provide username= or token= or both"
    headers = make_headers(token)
    if username:
        url = "https://api.github.com/users/{}".format(username)
    else:
        url = "https://api.github.com/user"
    return requests.get(url, headers=headers).json()


def paginate(url, headers=None):
    while url:
        response = requests.get(url, headers=headers)
        # For HTTP 204 no-content this yields an empty list
        if response.status_code == 204:
            return
        data = response.json()
        if isinstance(data, dict) and data.get("message"):
            raise GitHubError.from_response(response)
        try:
            url = response.links.get("next").get("url")
        except AttributeError:
            url = None
        yield data


def make_headers(token=None):
    headers = {}
    if token is not None:
        headers["Authorization"] = "token {}".format(token)
    return headers


def save_stars(db, user, stars):
    user_id = save_user(db, user)

    for star in stars:
        starred_at = star["starred_at"]
        repo = star["repo"]
        repo_id = save_repo(db, repo)
        db["stars"].insert(
            {"user": user_id, "repo": repo_id, "starred_at": starred_at},
            pk=("user", "repo"),
            foreign_keys=("user", "repo"),
            replace=True,
        )


def save_stargazers(db, repo_id, stargazers):
    for stargazer in stargazers:
        starred_at = stargazer["starred_at"]
        user_id = save_user(db, stargazer["user"])
        db["stars"].upsert(
            {"user": user_id, "repo": repo_id, "starred_at": starred_at},
            pk=("user", "repo"),
            foreign_keys=("user", "repo"),
        )


def save_releases(db, releases, repo_id=None):
    foreign_keys = [("author", "users", "id")]
    if repo_id:
        foreign_keys.append(("repo", "repos", "id"))
    for original in releases:
        # Ignore all of the _url fields except html_url
        release = {
            key: value
            for key, value in original.items()
            if key == "html_url" or not key.endswith("url")
        }
        assets = release.pop("assets") or []
        release["repo"] = repo_id
        release["author"] = save_user(db, release["author"])
        release_id = (
            db["releases"]
            .insert(
                release, pk="id", foreign_keys=foreign_keys, alter=True, replace=True
            )
            .last_pk
        )
        # Handle assets
        for asset in assets:
            asset["uploader"] = save_user(db, asset["uploader"])
            asset["release"] = release_id

        db["assets"].upsert_all(
            assets,
            pk="id",
            foreign_keys=[
                ("uploader", "users", "id"),
                ("release", "releases", "id"),
            ],
            alter=True,
        )


def save_contributors(db, contributors, repo_id):
    contributor_rows_to_add = []
    for contributor in contributors:
        contributions = contributor.pop("contributions")
        user_id = save_user(db, contributor)
        contributor_rows_to_add.append(
            {"repo_id": repo_id, "user_id": user_id, "contributions": contributions}
        )
    db["contributors"].insert_all(
        contributor_rows_to_add,
        pk=("repo_id", "user_id"),
        foreign_keys=[("repo_id", "repos", "id"), ("user_id", "users", "id")],
        replace=True,
    )


def save_tags(db, tags, repo_id):
    if not db["tags"].exists():
        db["tags"].create(
            {
                "repo": int,
                "name": str,
                "sha": str,
            },
            pk=("repo", "name"),
            foreign_keys=[("repo", "repos", "id")],
        )

    db["tags"].insert_all(
        (
            {
                "repo": repo_id,
                "name": tag["name"],
                "sha": tag["commit"]["sha"],
            }
            for tag in tags
        ),
        replace=True,
    )


def save_commits(db, commits, repo_id=None):
    foreign_keys = [
        ("author", "users", "id"),
        ("committer", "users", "id"),
        ("raw_author", "raw_authors", "id"),
        ("raw_committer", "raw_authors", "id"),
        ("repo", "repos", "id"),
    ]

    if not db["raw_authors"].exists():
        db["raw_authors"].create(
            {
                "id": str,
                "name": str,
                "email": str,
            },
            pk="id",
        )

    if not db["commits"].exists():
        # We explicitly create the table because otherwise we may create it
        # with incorrect column types, since author/committer can be null
        db["commits"].create(
            {
                "sha": str,
                "message": str,
                "author_date": str,
                "committer_date": str,
                "raw_author": str,
                "raw_committer": str,
                "repo": int,
                "author": int,
                "committer": int,
            },
            pk="sha",
            foreign_keys=foreign_keys,
        )

    for commit in commits:
        commit_to_insert = {
            "sha": commit["sha"],
            "message": commit["commit"]["message"],
            "author_date": commit["commit"]["author"]["date"],
            "committer_date": commit["commit"]["committer"]["date"],
            "raw_author": save_commit_author(db, commit["commit"]["author"]),
            "raw_committer": save_commit_author(db, commit["commit"]["committer"]),
        }
        commit_to_insert["repo"] = repo_id
        commit_to_insert["author"] = (
            save_user(db, commit["author"]) if commit["author"] else None
        )
        commit_to_insert["committer"] = (
            save_user(db, commit["committer"]) if commit["committer"] else None
        )
        db["commits"].insert(
            commit_to_insert,
            alter=True,
            replace=True,
        )


def save_commit_author(db, raw_author):
    name = raw_author.get("name")
    email = raw_author.get("email")
    return (
        db["raw_authors"]
        .insert(
            {
                "name": name,
                "email": email,
            },
            hash_id="id",
            replace=True,
        )
        .last_pk
    )


def ensure_foreign_keys(db):
    for expected_foreign_key in FOREIGN_KEYS:
        table, column, table2, column2 = expected_foreign_key
        if (
            expected_foreign_key not in db[table].foreign_keys
            and
            # Ensure all tables and columns exist
            db[table].exists()
            and db[table2].exists()
            and column in db[table].columns_dict
            and column2 in db[table2].columns_dict
        ):
            db[table].add_foreign_key(column, table2, column2)


def ensure_db_shape(db):
    "Ensure FTS is configured and expected FKS, views and (soon) indexes are present"
    # Foreign keys:
    ensure_foreign_keys(db)
    db.index_foreign_keys()

    # FTS:
    existing_tables = set(db.table_names())
    for table, columns in FTS_CONFIG.items():
        if "{}_fts".format(table) in existing_tables:
            continue
        if table not in existing_tables:
            continue
        db[table].enable_fts(columns, create_triggers=True)

    # Views:
    existing_views = set(db.view_names())
    existing_tables = set(db.table_names())
    for view, (tables, sql) in VIEWS.items():
        # Do all of the tables exist?
        if not tables.issubset(existing_tables):
            continue
        db.create_view(view, sql, replace=True)


def scrape_dependents(repo, verbose=False):
    # Optional dependency:
    from bs4 import BeautifulSoup

    url = "https://github.com/{}/network/dependents".format(repo)
    while url:
        if verbose:
            print(url)
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        repos = [
            a["href"].lstrip("/")
            for a in soup.select("a[data-hovercard-type=repository]")
        ]
        if verbose:
            print(repos)
        yield from repos
        # next page?
        try:
            next_link = soup.select(".paginate-container")[0].find("a", text="Next")
        except IndexError:
            break
        if next_link is not None:
            url = next_link["href"]
            time.sleep(1)
        else:
            url = None


def fetch_emojis(token=None):
    headers = make_headers(token)
    response = requests.get("https://api.github.com/emojis", headers=headers)
    response.raise_for_status()
    return [{"name": key, "url": value} for key, value in response.json().items()]


def fetch_image(url):
    return requests.get(url).content


def get(url, token=None, accept=None):
    headers = make_headers(token)
    if accept:
        headers["accept"] = accept
    if url.startswith("/"):
        url = "https://api.github.com{}".format(url)
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response


def fetch_readme(token, full_name, html=False):
    headers = make_headers(token)
    if html:
        headers["accept"] = "application/vnd.github.VERSION.html"
    url = "https://api.github.com/repos/{}/readme".format(full_name)
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    if html:
        return response.text
    else:
        return base64.b64decode(response.json()["content"]).decode("utf-8")


def fetch_workflows(token, full_name):
    headers = make_headers(token)
    url = "https://api.github.com/repos/{}/contents/.github/workflows".format(full_name)
    response = requests.get(url, headers=headers)
    if response.status_code == 404:
        return {}
    workflows = {}
    for item in response.json():
        name = item["name"]
        content = requests.get(item["download_url"]).text
        workflows[name] = content
    return workflows


def save_workflow(db, repo_id, filename, content):
    workflow = yaml.safe_load(content)
    jobs = workflow.pop("jobs", None) or {}
    # If there's a `True` key it was probably meant to be "on" - grr YAML
    if True in workflow:
        workflow["on"] = workflow.pop(True)
    # Replace workflow if one exists already
    existing = list(
        db["workflows"].rows_where("repo = ? and filename = ?", [repo_id, filename])
    )
    if existing:
        # Delete jobs, steps and this record
        existing_id = existing[0]["id"]
        db["steps"].delete_where(
            "job in (select id from jobs where workflow = ?)", [existing_id]
        )
        db["jobs"].delete_where("workflow = ?", [existing_id])
        db["workflows"].delete_where("id = ?", [existing_id])
    workflow_id = (
        db["workflows"]
        .insert(
            {
                **workflow,
                **{
                    "repo": repo_id,
                    "filename": filename,
                    "name": workflow.get("name", filename),
                },
            },
            pk="id",
            column_order=["id", "filename", "name"],
            alter=True,
            foreign_keys=["repo"],
        )
        .last_pk
    )
    db["workflows"].create_index(["repo", "filename"], unique=True, if_not_exists=True)
    for job_name, job_details in jobs.items():
        steps = job_details.pop("steps", None) or []
        job_id = (
            db["jobs"]
            .insert(
                {
                    **{
                        "workflow": workflow_id,
                        "name": job_name,
                        "repo": repo_id,
                    },
                    **job_details,
                },
                pk="id",
                alter=True,
                foreign_keys=["workflow", "repo"],
            )
            .last_pk
        )
        db["steps"].insert_all(
            [
                {
                    **{
                        "seq": i + 1,
                        "job": job_id,
                        "repo": repo_id,
                    },
                    **step,
                }
                for i, step in enumerate(steps)
            ],
            alter=True,
            pk="id",
            foreign_keys=["job", "repo"],
        )
