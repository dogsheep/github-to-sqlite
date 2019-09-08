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
    return db["users"].upsert(to_save, pk="id").last_pk


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


def fetch_all_issues(repo, token=None):
    headers = {}
    if token is not None:
        headers["Authorization"] = "token {}".format(token)
    url = "https://api.github.com/repos/{}/issues?state=all&filter=all".format(repo)
    for issues in paginate(url, headers):
        yield from issues


def paginate(url, headers=None):
    while url:
        response = requests.get(url, headers=headers)
        try:
            url = response.links.get("next").get("url")
        except AttributeError:
            url = None
        yield response.json()
