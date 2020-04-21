from github_to_sqlite import utils
import pytest
import pathlib
import sqlite_utils
from sqlite_utils.db import ForeignKey
import json


@pytest.fixture
def db():
    db = sqlite_utils.Database(memory=True)
    db["repos"].insert({"id": 1, "full_name": "dogsheep/github-to-sqlite"}, pk="id")
    db["issues"].insert({"id": 103, "number": 3, "repo": 1}, pk="id")
    issue_comments = json.load(
        open(pathlib.Path(__file__).parent / "issue-comments.json")
    )
    for comment in issue_comments:
        utils.save_issue_comment(db, comment)
    return db


def test_tables(db):
    assert {"users", "issue_comments", "issues", "repos"} == set(db.table_names())
    assert {
        ForeignKey(
            table="issue_comments",
            column="issue",
            other_table="issues",
            other_column="id",
        ),
        ForeignKey(
            table="issue_comments",
            column="user",
            other_table="users",
            other_column="id",
        ),
    } == set(db["issue_comments"].foreign_keys)


def test_issue_comments(db):
    issue_comment_rows = list(db["issue_comments"].rows)
    assert [
        {
            "html_url": "https://github.com/dogsheep/github-to-sqlite/issues/3#issuecomment-531516956",
            "issue_url": "https://api.github.com/repos/dogsheep/github-to-sqlite/issues/3",
            "id": 531516956,
            "node_id": "MDEyOklzc3VlQ29tbWVudDUzMTUxNjk1Ng==",
            "user": 9599,
            "created_at": "2019-09-14T21:56:31Z",
            "updated_at": "2019-09-14T21:56:31Z",
            "author_association": "COLLABORATOR",
            "body": "https://api.github.com/users/simonw/repos\r\n\r\nIt would be useful to be able to fetch stargazers, forks etc as well. Not sure if that should be a separate command or a `--stargazers` option to this command.\r\n\r\nProbably a separate command since `issues` is a separate command already.",
            "issue": 103,
        },
        {
            "html_url": "https://github.com/dogsheep/github-to-sqlite/issues/3#issuecomment-531517083",
            "issue_url": "https://api.github.com/repos/dogsheep/github-to-sqlite/issues/3",
            "id": 531517083,
            "node_id": "MDEyOklzc3VlQ29tbWVudDUzMTUxNzA4Mw==",
            "user": 9599,
            "created_at": "2019-09-14T21:58:42Z",
            "updated_at": "2019-09-14T21:58:42Z",
            "author_association": "COLLABORATOR",
            "body": "Split stargazers into #4",
            "issue": 103,
        },
        {
            "html_url": "https://github.com/dogsheep/github-to-sqlite/issues/4#issuecomment-531517138",
            "issue_url": "https://api.github.com/repos/dogsheep/github-to-sqlite/issues/4",
            "id": 531517138,
            "node_id": "MDEyOklzc3VlQ29tbWVudDUzMTUxNzEzOA==",
            "user": 9599,
            "created_at": "2019-09-14T21:59:59Z",
            "updated_at": "2019-09-14T21:59:59Z",
            "author_association": "COLLABORATOR",
            "body": "Paginate through https://api.github.com/repos/simonw/datasette/stargazers\r\n\r\nSend `Accept: application/vnd.github.v3.star+json` to get the `starred_at` dates.",
            # This issue wasn't in the DB so should be null:
            "issue": None,
        },
    ] == issue_comment_rows
