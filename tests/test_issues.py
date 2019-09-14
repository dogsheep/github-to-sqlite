from github_to_sqlite import utils
import pytest
import pathlib
import sqlite_utils
from sqlite_utils.db import ForeignKey
import json


@pytest.fixture
def issues():
    return json.load(open(pathlib.Path(__file__).parent / "issues.json"))


@pytest.fixture
def db(issues):
    db = sqlite_utils.Database(memory=True)
    utils.save_issues(db, issues)
    return db


def test_tables(db):
    assert {"issues", "users", "labels", "issues_labels", "milestones"} == set(
        db.table_names()
    )
    assert {
        ForeignKey(
            table="issues",
            column="milestone",
            other_table="milestones",
            other_column="id",
        ),
        ForeignKey(
            table="issues", column="assignee", other_table="users", other_column="id"
        ),
        ForeignKey(
            table="issues", column="user", other_table="users", other_column="id"
        ),
    } == set(db["issues"].foreign_keys)


def test_issues(db):
    issue_rows = list(db["issues"].rows)
    assert [
        {
            "id": 488343304,
            "node_id": "MDExOlB1bGxSZXF1ZXN0MzEzMzg0OTI2",
            "repo": "simonw/datasette",
            "number": 571,
            "title": "detect_fts now works with alternative table escaping",
            "user": 9599,
            "state": "closed",
            "locked": 0,
            "assignee": "9599",
            "milestone": None,
            "comments": 0,
            "created_at": "2019-09-03T00:23:39Z",
            "updated_at": "2019-09-03T00:32:28Z",
            "closed_at": "2019-09-03T00:32:28Z",
            "author_association": "OWNER",
            "body": "Fixes #570",
            "type": "pull",
            "pull_request": "simonw/datasette/pulls/571",
        },
        {
            "id": 489429284,
            "node_id": "MDU6SXNzdWU0ODk0MjkyODQ=",
            "repo": "simonw/datasette",
            "number": 572,
            "title": "Error running datasette publish with just --source_url",
            "user": 9599,
            "state": "open",
            "locked": 0,
            "assignee": None,
            "milestone": 2949431,
            "comments": 1,
            "created_at": "2019-09-04T22:19:22Z",
            "updated_at": "2019-09-04T22:20:38Z",
            "closed_at": None,
            "author_association": "OWNER",
            "body": '```\r\ndatasette publish now cleo.db \\\r\n    --source_url="https://twitter.com/cleopaws" \\\r\n```\r\nGave me this error:\r\n<img width="338" alt="Error_500" src="https://user-images.githubusercontent.com/9599/64295924-74b1e300-cf27-11e9-9aed-c69e99c97030.png">\r\n',
            "type": "issue",
            "pull_request": None,
        },
    ] == issue_rows


def test_users(db):
    user_rows = list(db["users"].rows)
    assert [
        {
            "login": "simonw",
            "id": 9599,
            "node_id": "MDQ6VXNlcjk1OTk=",
            "avatar_url": "https://avatars0.githubusercontent.com/u/9599?v=4",
            "gravatar_id": "",
            "html_url": "https://github.com/simonw",
            "type": "User",
            "site_admin": 0,
            "name": "simonw",
        }
    ] == user_rows


def test_milestones(db):
    milestone_rows = list(db["milestones"].rows)
    assert [
        {
            "html_url": "https://github.com/simonw/datasette/milestone/6",
            "id": 2949431,
            "node_id": "MDk6TWlsZXN0b25lMjk0OTQzMQ==",
            "number": 6,
            "title": "Custom templates edition",
            "description": "Ability to fully customize the HTML templates used to display datasette data.",
            "creator": 9599,
            "open_issues": 0,
            "closed_issues": 21,
            "state": "closed",
            "created_at": "2017-11-30T16:41:59Z",
            "updated_at": "2017-12-10T02:05:05Z",
            "due_on": None,
            "closed_at": "2017-12-10T02:05:05Z",
        }
    ] == milestone_rows
