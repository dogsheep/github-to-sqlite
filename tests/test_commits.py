from github_to_sqlite import utils
import pytest
import pathlib
import sqlite_utils
from sqlite_utils.db import ForeignKey
import json


@pytest.fixture
def commits():
    return json.load(open(pathlib.Path(__file__).parent / "commits.json"))


@pytest.fixture
def repo():
    return json.load(open(pathlib.Path(__file__).parent / "repo.json"))


@pytest.fixture
def db(commits, repo):
    db = sqlite_utils.Database(memory=True)
    utils.save_repo(db, repo)
    utils.save_commits(db, commits, repo["id"])
    return db


def test_tables(db):
    assert {"users", "licenses", "repos", "commits"} == set(db.table_names())
    assert {
        ForeignKey(
            table="commits", column="committer", other_table="users", other_column="id"
        ),
        ForeignKey(
            table="commits", column="repo", other_table="repos", other_column="id"
        ),
        ForeignKey(
            table="commits", column="author", other_table="users", other_column="id"
        ),
    } == set(db["commits"].foreign_keys)


def test_commits(db):
    commit_rows = list(db["commits"].rows)
    assert [
        {
            "sha": "9eb737090fafd0e5a7e314be48402374d99e9828",
            "message": "Release 0.6",
            "author_date": "2019-11-11T05:31:46Z",
            "committer_date": "2019-11-11T05:31:46Z",
            "repo": 207052882,
            "author": 9599,
            "committer": 9599,
        },
        {
            "sha": "1e6995a362e5b8f23331aafb84e631392eb81492",
            "message": "--auth is now optional, closes #9",
            "author_date": "2019-11-11T05:30:41Z",
            "committer_date": "2019-11-11T05:30:41Z",
            "repo": 207052882,
            "author": 9599,
            "committer": 9599,
        },
    ] == commit_rows
