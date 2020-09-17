from click.testing import CliRunner
from github_to_sqlite import cli
import pytest
import textwrap


@pytest.fixture
def mocked_paginated(requests_mock):
    requests_mock.get(
        "https://api.github.com/paginated",
        json=[{"id": 1, "title": "Item 1"}, {"id": 2, "title": "Item 2"}],
        headers={"link": '<https://api.github.com/paginated?page=2>; rel="next"'},
    )
    requests_mock.get(
        "https://api.github.com/paginated?page=2",
        json=[{"id": 3, "title": "Item 3"}, {"id": 4, "title": "Item 4"}],
        headers={"link": '<https://api.github.com/paginated>; rel="prev"'},
    )


@pytest.mark.parametrize("url", ["https://api.github.com/paginated", "/paginated"])
def test_get(mocked_paginated, url):
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli.cli, ["get", url])
        assert 0 == result.exit_code
        expected = textwrap.dedent(
            """
        [
            {
                "id": 1,
                "title": "Item 1"
            },
            {
                "id": 2,
                "title": "Item 2"
            }
        ]
        """
        ).strip()
        assert result.output.strip() == expected


@pytest.mark.parametrize(
    "nl,expected",
    (
        (
            False,
            textwrap.dedent(
                """
            [
                {
                    "id": 1,
                    "title": "Item 1"
                },
                {
                    "id": 2,
                    "title": "Item 2"
                },
                {
                    "id": 3,
                    "title": "Item 3"
                },
                {
                    "id": 4,
                    "title": "Item 4"
                }
            ]"""
            ).strip(),
        ),
        (
            True,
            textwrap.dedent(
                """
            {"id": 1, "title": "Item 1"}
            {"id": 2, "title": "Item 2"}
            {"id": 3, "title": "Item 3"}
            {"id": 4, "title": "Item 4"}
            """
            ).strip(),
        ),
    ),
)
def test_get_paginate(mocked_paginated, nl, expected):
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli.cli,
            ["get", "https://api.github.com/paginated", "--paginate"]
            + (["--nl"] if nl else []),
        )
        assert 0 == result.exit_code
        assert result.output.strip() == expected
