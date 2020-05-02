from github_to_sqlite import cli
from click.testing import CliRunner
import json
import sqlite_utils
import pathlib

REPO = json.load(open(pathlib.Path(__file__).parent / "repo.json"))


def test_scrape_dependents(requests_mock):
    requests_mock.get(
        "https://github.com/dogsheep/github-to-sqlite/network/dependents",
        text="""
        <a data-hovercard-type="repository" href="/simonw/foo">
        <a data-hovercard-type="repository" href="/simonw/bar">
        <div class="paginate-container">
            <a href="https://github.com/dogsheep/github-to-sqlite/network/dependents?dependents_after=abc">Next</a>
        </div>
        """,
    )
    requests_mock.get(
        "https://github.com/dogsheep/github-to-sqlite/network/dependents?dependents_after=abc",
        text="""
        <a data-hovercard-type="repository" href="/simonw/baz">
        """,
    )
    requests_mock.get(
        "https://api.github.com/repos/dogsheep/github-to-sqlite", json=REPO
    )
    requests_mock.get(
        "https://api.github.com/repos/simonw/foo",
        json=dict(REPO, id=1, full_name="simonw/foo"),
    )
    requests_mock.get(
        "https://api.github.com/repos/simonw/bar",
        json=dict(REPO, id=2, full_name="simonw/bar"),
    )
    requests_mock.get(
        "https://api.github.com/repos/simonw/baz",
        json=dict(REPO, id=3, full_name="simonw/baz"),
    )
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli.cli, ["scrape-dependents", "scrape.db", "dogsheep/github-to-sqlite"]
        )
        assert 0 == result.exit_code
        db = sqlite_utils.Database("scrape.db")
        assert {"repos", "dependents"}.issubset(db.table_names())
        assert {1, 2, 3, 207052882} == set(
            r[0] for r in db.conn.execute("select id from repos").fetchall()
        )
        pairs = [(r["repo"], r["dependent"]) for r in db["dependents"].rows]
        assert [(207052882, 1), (207052882, 2), (207052882, 3)] == pairs

        # Finally, test that dependent_repos view
        rows = list(db["dependent_repos"].rows)
        assert [
            {
                "repo": "dogsheep/github-to-sqlite",
                "dependent": "https://github.com/simonw/foo",
                "dependent_created": "2019-09-08T02:50:28Z",
                "dependent_updated": "2019-11-07T19:14:34Z",
                "dependent_stars": 6,
                "dependent_watchers": 6,
            },
            {
                "repo": "dogsheep/github-to-sqlite",
                "dependent": "https://github.com/simonw/bar",
                "dependent_created": "2019-09-08T02:50:28Z",
                "dependent_updated": "2019-11-07T19:14:34Z",
                "dependent_stars": 6,
                "dependent_watchers": 6,
            },
            {
                "repo": "dogsheep/github-to-sqlite",
                "dependent": "https://github.com/simonw/baz",
                "dependent_created": "2019-09-08T02:50:28Z",
                "dependent_updated": "2019-11-07T19:14:34Z",
                "dependent_stars": 6,
                "dependent_watchers": 6,
            },
        ] == rows
