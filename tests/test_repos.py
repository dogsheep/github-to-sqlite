import base64
import pytest
import pathlib
import sqlite_utils
from sqlite_utils.db import ForeignKey
import json
from click.testing import CliRunner
from github_to_sqlite import cli
import pytest


@pytest.fixture
def mocked(requests_mock):
    requests_mock.get(
        "https://api.github.com/repos/dogsheep/github-to-sqlite",
        json=json.load(open(pathlib.Path(__file__).parent / "repo.json")),
    )
    requests_mock.get(
        "https://api.github.com/repos/dogsheep/github-to-sqlite/readme",
        json={"content": base64.b64encode(b"# This is the README").decode("utf-8")},
    )
    requests_mock.get(
        "https://api.github.com/repos/dogsheep/github-to-sqlite/readme",
        text="<h1>This is the README</h1>",
        additional_matcher=lambda request: request.headers.get("accept")
        == "application/vnd.github.VERSION.html",
    )


def test_repos(mocked, tmpdir):
    runner = CliRunner()
    db_path = str(tmpdir / "test.db")
    result = runner.invoke(
        cli.cli,
        [
            "repos",
            db_path,
            "-r",
            "dogsheep/github-to-sqlite",
            "--readme",
            "--readme-html",
        ],
    )
    assert 0 == result.exit_code
    db = sqlite_utils.Database(db_path)
    assert db.table_names() == [
        "users",
        "licenses",
        "repos",
        "licenses_fts",
        "licenses_fts_data",
        "licenses_fts_idx",
        "licenses_fts_docsize",
        "licenses_fts_config",
        "repos_fts",
        "repos_fts_data",
        "repos_fts_idx",
        "repos_fts_docsize",
        "repos_fts_config",
        "users_fts",
        "users_fts_data",
        "users_fts_idx",
        "users_fts_docsize",
        "users_fts_config",
    ]
    assert db["repos"].count == 1
    repo = next(iter(db["repos"].rows))
    assert repo["full_name"] == "dogsheep/github-to-sqlite"
    assert repo["readme"] == "# This is the README"
    assert repo["readme_html"] == "<h1>This is the README</h1>"
