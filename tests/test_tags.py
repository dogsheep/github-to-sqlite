from github_to_sqlite import utils
import pytest
import pathlib
import sqlite_utils
from sqlite_utils.db import ForeignKey
import json


@pytest.fixture
def tags():
    return json.load(open(pathlib.Path(__file__).parent / "tags.json"))


@pytest.fixture
def repo():
    return json.load(open(pathlib.Path(__file__).parent / "repo.json"))


@pytest.fixture
def db(tags, repo):
    db = sqlite_utils.Database(memory=True)
    utils.save_repo(db, repo)
    utils.save_tags(db, tags, repo["id"])
    return db


def test_tables(db):
    assert {"users", "tags", "licenses", "repos"} == set(db.table_names())
    assert {
        ForeignKey(
            table="tags", column="repo_id", other_table="repos", other_column="id"
        )
    } == set(db["tags"].foreign_keys)


def test_tags(db):
    tags_rows = list(db["tags"].rows)
    assert [
        {
            "repo_id": 207052882,
            "name": "2.3",
            "sha": "7090e43d804724ef3b31ae5ca9efd6ac05f76cbc",
        },
        {
            "repo_id": 207052882,
            "name": "2.2",
            "sha": "4fe69783b55465e7692a807d3a02a710f69c9c42",
        },
    ] == tags_rows
