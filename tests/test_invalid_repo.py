from click.testing import CliRunner
from github_to_sqlite import cli
import pytest


@pytest.mark.parametrize("bad_repo", ["not-a-repo", "too/many/slashes", ""])
def test_issues_rejects_malformed_repo(bad_repo):
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli.cli, ["issues", "test.db", bad_repo])
        assert result.exit_code == 1
        assert not isinstance(result.exception, ValueError)
        assert "owner/name" in result.output
