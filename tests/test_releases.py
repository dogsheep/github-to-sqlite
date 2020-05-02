from github_to_sqlite import utils
import pytest
import pathlib
import sqlite_utils
from sqlite_utils.db import ForeignKey
import json


@pytest.fixture
def releases():
    return json.load(open(pathlib.Path(__file__).parent / "releases.json"))


@pytest.fixture
def repo():
    return json.load(open(pathlib.Path(__file__).parent / "repo.json"))


@pytest.fixture
def db(releases, repo):
    db = sqlite_utils.Database(memory=True)
    utils.save_repo(db, repo)
    utils.save_releases(db, releases, repo["id"])
    utils.ensure_db_shape(db)
    return db


def test_tables(db):
    assert {"users", "licenses", "repos", "releases", "assets"}.issubset(
        db.table_names()
    )
    assert {
        ForeignKey(
            table="releases", column="author", other_table="users", other_column="id"
        ),
        ForeignKey(
            table="releases", column="repo", other_table="repos", other_column="id"
        ),
    } == set(db["releases"].foreign_keys)
    assert {
        ForeignKey(
            table="assets", column="uploader", other_table="users", other_column="id"
        ),
        ForeignKey(
            table="assets", column="release", other_table="releases", other_column="id"
        ),
    } == set(db["assets"].foreign_keys)


def test_releases(db):
    release_rows = list(db["releases"].rows)
    assert [
        {
            "html_url": "https://github.com/dogsheep/github-to-sqlite/releases/tag/0.1.1",
            "id": 19993251,
            "node_id": "MDc6UmVsZWFzZTE5OTkzMjUx",
            "tag_name": "0.1.1",
            "target_commitish": "master",
            "name": "0.1.1",
            "draft": 0,
            "author": 9599,
            "prerelease": 0,
            "created_at": "2019-09-14T19:19:33Z",
            "published_at": "2019-09-14T19:42:08Z",
            "body": "* Fix bug in authentication handling code",
            "repo": 207052882,
        },
        {
            "html_url": "https://github.com/dogsheep/github-to-sqlite/releases/tag/0.2",
            "id": 19993751,
            "node_id": "MDc6UmVsZWFzZTE5OTkzNzUx",
            "tag_name": "0.2",
            "target_commitish": "master",
            "name": "0.2",
            "draft": 0,
            "author": 9599,
            "prerelease": 0,
            "created_at": "2019-09-14T21:31:17Z",
            "published_at": "2019-09-14T21:32:34Z",
            "body": "* Added the `github-to-sqlite starred` command for retrieving starred repos, #1 ",
            "repo": 207052882,
        },
        {
            "html_url": "https://github.com/dogsheep/github-to-sqlite/releases/tag/0.3",
            "id": 19993820,
            "node_id": "MDc6UmVsZWFzZTE5OTkzODIw",
            "tag_name": "0.3",
            "target_commitish": "master",
            "name": "0.3",
            "draft": 0,
            "author": 9599,
            "prerelease": 0,
            "created_at": "2019-09-14T21:49:27Z",
            "published_at": "2019-09-14T21:50:01Z",
            "body": "* `license` is now extracted from the `repos` table into a separate `licenses` table with a foreign key, #2\r\n\r\n",
            "repo": 207052882,
        },
        {
            "html_url": "https://github.com/dogsheep/github-to-sqlite/releases/tag/0.4",
            "id": 20031553,
            "node_id": "MDc6UmVsZWFzZTIwMDMxNTUz",
            "tag_name": "0.4",
            "target_commitish": "master",
            "name": "0.4",
            "draft": 0,
            "author": 9599,
            "prerelease": 0,
            "created_at": "2019-09-17T00:18:37Z",
            "published_at": "2019-09-17T00:19:42Z",
            "body": "* Added `github-to-sqlite repos` command, #3 ",
            "repo": 207052882,
        },
        {
            "html_url": "https://github.com/dogsheep/github-to-sqlite/releases/tag/0.5",
            "id": 20663605,
            "node_id": "MDc6UmVsZWFzZTIwNjYzNjA1",
            "tag_name": "0.5",
            "target_commitish": "master",
            "name": "0.5",
            "draft": 0,
            "author": 9599,
            "prerelease": 0,
            "created_at": "2019-10-13T05:28:24Z",
            "published_at": "2019-10-13T05:30:05Z",
            "body": "* New command: `github-to-sqlite issue-comments` for importing comments on issues - #7\r\n* `github-to-sqlite issues` now accepts optional `--issue=1` argument\r\n* Fixed bug inserting users into already-created table with wrong columns - #6",
            "repo": 207052882,
        },
    ] == release_rows
    asset_rows = list(db["assets"].rows)
    assert [
        {
            "url": "https://api.github.com/repos/dogsheep/github-to-sqlite/releases/assets/11811946",
            "id": 11811946,
            "node_id": "MDEyOlJlbGVhc2VBc3NldDExODExOTQ2",
            "name": "checksums.txt",
            "label": "",
            "uploader": 9599,
            "content_type": "text/plain; charset=utf-8",
            "state": "uploaded",
            "size": 600,
            "download_count": 2,
            "created_at": "2019-03-30T16:56:44Z",
            "updated_at": "2019-03-30T16:56:44Z",
            "browser_download_url": "https://github.com/dogsheep/github-to-sqlite/releases/download/v0.1.0/checksums.txt",
            "release": 19993251,
        }
    ] == asset_rows


def test_recent_releases_view(db):
    assert "recent_releases" in db.view_names()
    rows = list(db["recent_releases"].rows)
    assert [
        {
            "rowid": 207052882,
            "repo": "https://github.com/dogsheep/github-to-sqlite",
            "release": "https://github.com/dogsheep/github-to-sqlite/releases/tag/0.5",
            "date": "2019-10-13",
            "body_markdown": "* New command: `github-to-sqlite issue-comments` for importing comments on issues - #7\r\n* `github-to-sqlite issues` now accepts optional `--issue=1` argument\r\n* Fixed bug inserting users into already-created table with wrong columns - #6",
            "published_at": "2019-10-13T05:30:05Z",
            "topics": "[]",
        },
        {
            "rowid": 207052882,
            "repo": "https://github.com/dogsheep/github-to-sqlite",
            "release": "https://github.com/dogsheep/github-to-sqlite/releases/tag/0.4",
            "date": "2019-09-17",
            "body_markdown": "* Added `github-to-sqlite repos` command, #3 ",
            "published_at": "2019-09-17T00:19:42Z",
            "topics": "[]",
        },
        {
            "rowid": 207052882,
            "repo": "https://github.com/dogsheep/github-to-sqlite",
            "release": "https://github.com/dogsheep/github-to-sqlite/releases/tag/0.3",
            "date": "2019-09-14",
            "body_markdown": "* `license` is now extracted from the `repos` table into a separate `licenses` table with a foreign key, #2\r\n\r\n",
            "published_at": "2019-09-14T21:50:01Z",
            "topics": "[]",
        },
        {
            "rowid": 207052882,
            "repo": "https://github.com/dogsheep/github-to-sqlite",
            "release": "https://github.com/dogsheep/github-to-sqlite/releases/tag/0.2",
            "date": "2019-09-14",
            "body_markdown": "* Added the `github-to-sqlite starred` command for retrieving starred repos, #1 ",
            "published_at": "2019-09-14T21:32:34Z",
            "topics": "[]",
        },
        {
            "rowid": 207052882,
            "repo": "https://github.com/dogsheep/github-to-sqlite",
            "release": "https://github.com/dogsheep/github-to-sqlite/releases/tag/0.1.1",
            "date": "2019-09-14",
            "body_markdown": "* Fix bug in authentication handling code",
            "published_at": "2019-09-14T19:42:08Z",
            "topics": "[]",
        },
    ] == rows
