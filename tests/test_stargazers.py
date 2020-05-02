from github_to_sqlite import utils
import json
import pathlib
import pytest
import sqlite_utils
from sqlite_utils.db import ForeignKey


@pytest.fixture
def stargazers():
    return json.load(open(pathlib.Path(__file__).parent / "stargazers.json"))


@pytest.fixture
def repo():
    return json.load(open(pathlib.Path(__file__).parent / "repo.json"))


@pytest.fixture
def db(stargazers, repo):
    db = sqlite_utils.Database(memory=True)
    utils.save_repo(db, repo)
    utils.save_stargazers(db, repo["id"], stargazers)
    utils.ensure_db_shape(db)
    return db


def test_stargazers_rows(db):
    rows = list(db["stars"].rows)
    assert [
        {"user": 233977, "repo": 207052882, "starred_at": "2019-09-08T05:00:56Z"},
        {"user": 6964781, "repo": 207052882, "starred_at": "2019-09-08T10:29:28Z"},
    ] == rows
