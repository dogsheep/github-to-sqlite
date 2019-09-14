from github_to_sqlite import utils
import json
import pathlib
import pytest
import sqlite_utils


@pytest.fixture
def starred():
    return json.load(open(pathlib.Path(__file__).parent / "starred.json"))


@pytest.fixture
def user():
    return json.load(open(pathlib.Path(__file__).parent / "user.json"))


@pytest.fixture
def db(starred, user):
    db = sqlite_utils.Database(memory=True)
    utils.save_stars(db, user, starred)
    return db


def test_tables(db):
    assert {"repos", "stars", "users"} == set(db.table_names())


def test_repos(db):
    repos = list(db["repos"].rows)
    assert [
        {
            "id": 123,
            "node_id": "MDEwOlJlcG9zaccbcckyMDgzNjkxNTM=",
            "name": "repo-name",
            "full_name": "owner-name/repo-name",
            "private": 0,
            "owner": 456,
            "html_url": "https://github.com/owner-name/repo-name",
            "description": "Repo description",
            "fork": 0,
            "created_at": "2019-09-14T00:50:14Z",
            "updated_at": "2019-09-14T14:28:32Z",
            "pushed_at": "2019-09-14T07:02:40Z",
            "homepage": None,
            "size": 7,
            "stargazers_count": 2,
            "watchers_count": 2,
            "language": "Python",
            "has_issues": 1,
            "has_projects": 1,
            "has_downloads": 1,
            "has_wiki": 1,
            "has_pages": 0,
            "forks_count": 0,
            "archived": 0,
            "disabled": 0,
            "open_issues_count": 0,
            "license": None,
            "forks": 0,
            "open_issues": 0,
            "watchers": 2,
            "default_branch": "master",
        }
    ] == repos


def test_stars(db):
    stars = list(db["stars"].rows)
    assert [{"user": 9599, "repo": 123, "starred_at": "2019-09-14T08:35:12Z"}] == stars
