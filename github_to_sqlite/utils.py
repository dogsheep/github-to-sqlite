import requests


def save_issues(db, issues):
    if "milestones" not in db.table_names():
        db["milestones"].create({"id": int}, pk="id")
    for original in issues:
        # Ignore all of the _url fields
        issue = {
            key: value for key, value in original.items() if not key.endswith("url")
        }
        # Add repo key
        issue["repo"] = original["repository_url"].split(
            "https://api.github.com/repos/"
        )[1]
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
            issue["milestone"] = save_milestone(db, issue["milestone"])
        # For the moment we ignore the assignees=[] array but we DO turn assignee
        # singular into a foreign key reference
        issue.pop("assignees", None)
        if issue["assignee"]:
            issue["assignee"] = save_user(db, issue["assignee"])
        # Add a type field to distinguish issues from pulls
        issue["type"] = "pull" if issue.get("pull_request") else "issue"
        # Insert record
        table = db["issues"].upsert(
            issue,
            pk="id",
            foreign_keys=[
                ("user", "users", "id"),
                ("assignee", "users", "id"),
                ("milestone", "milestones", "id"),
            ],
            alter=True,
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


def save_milestone(db, milestone):
    milestone = dict(milestone)
    milestone["creator"] = save_user(db, milestone["creator"])
    milestone.pop("labels_url", None)
    milestone.pop("url", None)
    return (
        db["milestones"]
        .upsert(
            milestone, pk="id", foreign_keys=[("creator", "users", "id")], alter=True
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
            "number = :number and repo = :repo",
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
        .upsert(comment, pk="id", foreign_keys=("user", "issue"), alter=True)
        .last_pk
    )
    return last_pk


def fetch_repo(repo, token=None):
    headers = make_headers(token)
    owner, slug = repo.split("/")
    url = "https://api.github.com/repos/{}/{}".format(owner, slug)
    return requests.get(url, headers=headers).json()


def save_repo(db, repo):
    # Remove all url fields except html_url
    to_save = {
        key: value
        for key, value in repo.items()
        if (key == "html_url") or not key.endswith("url")
    }
    to_save["owner"] = save_user(db, to_save["owner"])
    to_save["license"] = save_license(db, to_save["license"])
    repo_id = (
        db["repos"]
        .upsert(to_save, pk="id", foreign_keys=(("owner", "users", "id"),), alter=True)
        .last_pk
    )
    return repo_id


def save_license(db, license):
    if license is None:
        return None
    return db["licenses"].upsert(license, pk="key").last_pk


def ensure_repo_fts(db):
    if "repos_fts" not in db.table_names():
        db["repos"].enable_fts(["name", "description"], create_triggers=True)


def ensure_releases_fts(db):
    if "releases_fts" not in db.table_names():
        db["releases"].enable_fts(["name", "body"], create_triggers=True)


def ensure_foreign_keys(db):
    for expected_key in (("repos", "license", "licenses", "key"),):
        if expected_key not in db[expected_key[0]].foreign_keys:
            db[expected_key[0]].add_foreign_key(*expected_key[1:])


def fetch_issues(repo, token=None, issue=None):
    headers = make_headers(token)
    if issue is not None:
        url = "https://api.github.com/repos/{}/issues/{}".format(repo, issue)
        yield from [requests.get(url).json()]
    else:
        url = "https://api.github.com/repos/{}/issues?state=all&filter=all".format(repo)
        for issues in paginate(url, headers):
            yield from issues


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


def fetch_releases(repo, token=None, issue=None):
    headers = make_headers(token)
    url = "https://api.github.com/repos/{}/releases".format(repo)
    for releases in paginate(url, headers):
        yield from releases


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
        try:
            url = response.links.get("next").get("url")
        except AttributeError:
            url = None
        yield response.json()


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
        issue = {
            key: value
            for key, value in original.items()
            if key == "html_url" or not key.endswith("url")
        }
        issue["repo"] = repo_id
        issue["author"] = save_user(db, issue["author"])
        db["releases"].upsert(issue, pk="id", foreign_keys=foreign_keys, alter=True)
