import base64
import pytest
import pathlib
import sqlite_utils
from sqlite_utils.db import ForeignKey
import json
from click.testing import CliRunner
from github_to_sqlite import cli
import pytest

README_HTML = """
<li><a href="#filtering-tables">Filtering tables</a></li>
...
<h3><a id="user-content-filtering-tables" class="anchor" aria-hidden="true" href="#filtering-tables">#</a>Filtering tables</h3>
"""
EXPECTED_README_HTML = """
<li><a href="#user-content-filtering-tables">Filtering tables</a></li>
...
<h3><a id="user-content-filtering-tables" class="anchor" aria-hidden="true" href="#user-content-filtering-tables">#</a>Filtering tables</h3>
"""


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
        text=README_HTML,
        additional_matcher=lambda request: request.headers.get("accept")
        == "application/vnd.github.VERSION.html",
    )


def test_repos(mocked, tmpdir):
    db_path = _run_repos(tmpdir)
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
    assert repo["readme_html"] is not None


def test_repos_readme_not_available(requests_mock, tmpdir):
    requests_mock.get(
        "https://api.github.com/repos/dogsheep/github-to-sqlite",
        json=json.load(open(pathlib.Path(__file__).parent / "repo.json")),
    )
    requests_mock.get(
        "https://api.github.com/repos/dogsheep/github-to-sqlite/readme",
        status_code=400,
    )
    db_path = _run_repos(tmpdir)
    db = sqlite_utils.Database(db_path)
    row = list(db["repos"].rows)[0]
    assert row["name"] == "github-to-sqlite"
    assert row["readme"] is None
    assert row["readme_html"] is None


def test_readme_internal_links_are_rewritten(mocked, tmpdir):
    # https://github.com/dogsheep/github-to-sqlite/issues/58
    db_path = _run_repos(tmpdir)
    db = sqlite_utils.Database(db_path)
    assert list(db["repos"].rows)[0]["readme_html"] == EXPECTED_README_HTML


def _run_repos(tmpdir):
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
    return db_path
