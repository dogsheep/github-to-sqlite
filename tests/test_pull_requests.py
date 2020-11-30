from github_to_sqlite import utils
import pytest
import pathlib
import sqlite_utils
from sqlite_utils.db import ForeignKey
import json


@pytest.fixture
def pull_requests():
    return json.load(open(pathlib.Path(__file__).parent / "pull_requests.json"))


@pytest.fixture
def db(pull_requests):
    db = sqlite_utils.Database(memory=True)
    db["repos"].insert(
        {"id": 1},
        pk="id",
        columns={"organization": int, "topics": str, "name": str, "description": str},
    )
    utils.save_pull_requests(db, pull_requests, {"id": 1})
    return db


def test_tables(db):
    assert {"pull_requests", "users", "repos", "milestones"} == set(db.table_names())
    assert set(db["pull_requests"].foreign_keys) == {
        ForeignKey(
            table="pull_requests",
            column="merged_by",
            other_table="users",
            other_column="id",
        ),
        ForeignKey(
            table="pull_requests",
            column="assignee",
            other_table="users",
            other_column="id",
        ),
        ForeignKey(
            table="pull_requests",
            column="milestone",
            other_table="milestones",
            other_column="id",
        ),
        ForeignKey(
            table="pull_requests", column="repo", other_table="repos", other_column="id"
        ),
        ForeignKey(
            table="pull_requests", column="user", other_table="users", other_column="id"
        ),
    }


def test_pull_requests(db):
    pull_request_rows = list(db["pull_requests"].rows)
    assert [
        {
            "id": 313384926,
            "node_id": "MDExOlB1bGxSZXF1ZXN0MzEzMzg0OTI2",
            "number": 571,
            "state": "closed",
            "locked": 0,
            "title": "detect_fts now works with alternative table escaping",
            "user": 9599,
            "body": "Fixes #570",
            "created_at": "2019-09-03T00:23:39Z",
            "updated_at": "2019-09-03T00:32:28Z",
            "closed_at": "2019-09-03T00:32:28Z",
            "merged_at": "2019-09-03T00:32:28Z",
            "merge_commit_sha": "2dc5c8dc259a0606162673d394ba8cc1c6f54428",
            "assignee": None,
            "milestone": None,
            "draft": 0,
            "head": "a85239f69261c10f1a9f90514c8b5d113cb94585",
            "base": "f04deebec4f3842f7bd610cd5859de529f77d50e",
            "author_association": "OWNER",
            "merged": 1,
            "mergeable": None,
            "rebaseable": None,
            "mergeable_state": "unknown",
            "merged_by": 9599,
            "comments": 0,
            "review_comments": 0,
            "maintainer_can_modify": 0,
            "commits": 1,
            "additions": 7,
            "deletions": 3,
            "changed_files": 2,
            "repo": 1,
            "url": "https://github.com/simonw/datasette/pull/571",
        }
    ] == pull_request_rows


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


def test_foreign_keys(db):
    assert db["pull_requests"].foreign_keys == [
        ForeignKey(
            table="pull_requests", column="repo", other_table="repos", other_column="id"
        ),
        ForeignKey(
            table="pull_requests",
            column="merged_by",
            other_table="users",
            other_column="id",
        ),
        ForeignKey(
            table="pull_requests",
            column="milestone",
            other_table="milestones",
            other_column="id",
        ),
        ForeignKey(
            table="pull_requests",
            column="assignee",
            other_table="users",
            other_column="id",
        ),
        ForeignKey(
            table="pull_requests", column="user", other_table="users", other_column="id"
        ),
    ]
