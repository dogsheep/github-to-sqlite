# github-to-sqlite

[![PyPI](https://img.shields.io/pypi/v/github-to-sqlite.svg)](https://pypi.org/project/github-to-sqlite/)
[![Changelog](https://img.shields.io/github/v/release/dogsheep/github-to-sqlite?include_prereleases&label=changelog)](https://github.com/dogsheep/github-to-sqlite/releases)
[![Tests](https://github.com/dogsheep/github-to-sqlite/workflows/Test/badge.svg)](https://github.com/dogsheep/github-to-sqlite/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/dogsheep/github-to-sqlite/blob/main/LICENSE)

Save data from GitHub to a SQLite database.

<!-- toc -->

- [Demo](#demo)
- [How to install](#how-to-install)
- [Authentication](#authentication)
- [Fetching issues for a repository](#fetching-issues-for-a-repository)
- [Fetching pull requests for a repository](#fetching-pull-requests-for-a-repository)
- [Fetching issue comments for a repository](#fetching-issue-comments-for-a-repository)
- [Fetching commits for a repository](#fetching-commits-for-a-repository)
- [Fetching releases for a repository](#fetching-releases-for-a-repository)
- [Fetching tags for a repository](#fetching-tags-for-a-repository)
- [Fetching contributors to a repository](#fetching-contributors-to-a-repository)
- [Fetching repos belonging to a user or organization](#fetching-repos-belonging-to-a-user-or-organization)
- [Fetching specific repositories](#fetching-specific-repositories)
- [Fetching repos that have been starred by a user](#fetching-repos-that-have-been-starred-by-a-user)
- [Fetching users that have starred specific repos](#fetching-users-that-have-starred-specific-repos)
- [Fetching GitHub Actions workflows](#fetching-github-actions-workflows)
- [Scraping dependents for a repository](#scraping-dependents-for-a-repository)
- [Fetching emojis](#fetching-emojis)
- [Making authenticated API calls](#making-authenticated-api-calls)

<!-- tocstop -->

## Demo

https://github-to-sqlite.dogsheep.net/ hosts a [Datasette](https://datasette.readthedocs.io/) demo of a database created by [running this tool](https://github.com/dogsheep/github-to-sqlite/blob/main/.github/workflows/deploy-demo.yml#L40-L60) against all of the repositories in the [Dogsheep GitHub organization](https://github.com/dogsheep), plus the [datasette](https://github.com/simonw/datasette) and [sqlite-utils](https://github.com/simonw/sqlite-utils) repositories.

## How to install

    $ pip install github-to-sqlite

## Authentication

Create a GitHub personal access token: https://github.com/settings/tokens

Run this command and paste in your new token:

    $ github-to-sqlite auth

This will create a file called `auth.json` in your current directory containing the required value. To save the file at a different path or filename, use the `--auth=myauth.json` option.

As an alternative to using an `auth.json` file you can add your access token to an environment variable called `GITHUB_TOKEN`.

## Fetching issues for a repository

The `issues` command retrieves all of the issues belonging to a specified repository.

    $ github-to-sqlite issues github.db simonw/datasette

If an `auth.json` file is present it will use the token from that file. It works without authentication for public repositories but you should be aware that GitHub have strict IP-based rate limits for unauthenticated requests.

You can point to a different location of `auth.json` using `-a`:

    $ github-to-sqlite issues github.db simonw/datasette -a /path/to/auth.json

You can use the `--issue` option one or more times to load specific issues:

    $ github-to-sqlite issues github.db simonw/datasette --issue=1

Example: [issues table](https://github-to-sqlite.dogsheep.net/github/issues)

## Fetching pull requests for a repository

While pull requests are a type of issue, you will get more information on pull requests by pulling them separately. For example, whether a pull request has been merged and when.

Following the API of issues, the `pull-requests` command retrieves all of the pull requests belonging to a specified repository.

    $ github-to-sqlite pull-requests github.db simonw/datasette

You can use the `--pull-request` option one or more times to load specific pull request:

    $ github-to-sqlite pull-requests github.db simonw/datasette --pull-request=81

Note that the `merged_by` column on the `pull_requests` table will only be populated for pull requests that are loaded using the `--pull-request` option - the GitHub API does not return this field for pull requests that are loaded in bulk.

Example: [pull_requests table](https://github-to-sqlite.dogsheep.net/github/pull_requests)

## Fetching issue comments for a repository

The `issue-comments` command retrieves all of the comments on all of the issues in a repository.

It is recommended you run `issues` first, so that each imported comment can have a foreign key poining to its issue.

    $ github-to-sqlite issues github.db simonw/datasette
    $ github-to-sqlite issue-comments github.db simonw/datasette

You can use the `--issue` option to only load comments for a specific issue within that repository, for example:

    $ github-to-sqlite issue-comments github.db simonw/datasette --issue=1

Example: [issue_comments table](https://github-to-sqlite.dogsheep.net/github/issue_comments)

## Fetching commits for a repository

The `commits` command retrieves details of all of the commits for one or more repositories. It currently fetches the sha, commit message and author and committer details - it does no retrieve the full commit body.

    $ github-to-sqlite commits github.db simonw/datasette simonw/sqlite-utils

The command accepts one or more repositories.

By default it will stop as soon as it sees a commit that has previously been retrieved. You can force it to retrieve all commits (including those that have been previously inserted) using `--all`.

Example: [commits table](https://github-to-sqlite.dogsheep.net/github/commits)

## Fetching releases for a repository

The `releases` command retrieves the releases for one or more repositories.

    $ github-to-sqlite releases github.db simonw/datasette simonw/sqlite-utils

The command accepts one or more repositories.

Example: [releases table](https://github-to-sqlite.dogsheep.net/github/releases)

## Fetching tags for a repository

The `tags` command retrieves all of the tags for one or more repositories.

    $ github-to-sqlite tags github.db simonw/datasette simonw/sqlite-utils

Example: [tags table](https://github-to-sqlite.dogsheep.net/github/tags)

## Fetching contributors to a repository

The `contributors` command retrieves details of all of the contributors for one or more repositories.

    $ github-to-sqlite contributors github.db simonw/datasette simonw/sqlite-utils

The command accepts one or more repositories. It populates a `contributors` table, with foreign keys to `repos` and `users` and a `contributions` table listing the number of commits to that repository for each contributor.

Example: [contributors table](https://github-to-sqlite.dogsheep.net/github/contributors)

## Fetching repos belonging to a user or organization

The `repos` command fetches repos belonging to a user or organization.

Without any other arguments, this command will fetch all repos that the currently authenticated user owns, collaborates on or can access via one of their organizations:

    $ github-to-sqlite repos github.db

To fetch repos belonging to a specific user or organization, provide their username as an argument:

    $ github-to-sqlite repos github.db dogsheep # organization
    $ github-to-sqlite repos github.db simonw # user

You can pass more than one username to fetch for multiple users or organizations at once:

    $ github-to-sqlite repos github.db simonw dogsheep

Add the `--readme` option to save the README for the repo in a column called `readme`. Add `--readme-html` to save the HTML rendered version of the README into a collumn called `readme_html`.

Example: [repos table](https://github-to-sqlite.dogsheep.net/github/repos)

## Fetching specific repositories

You can use `-r` with the `repos` command one or more times to fetch just specific repositories.

    $ github-to-sqlite repos github.db -r simonw/datasette -r dogsheep/github-to-sqlite

## Fetching repos that have been starred by a user

The `starred` command fetches the repos that have been starred by a user.

    $ github-to-sqlite starred github.db simonw

If you are using an `auth.json` file you can omit the username to retrieve the starred repos for the authenticated user.

Example: [stars table](https://github-to-sqlite.dogsheep.net/github/stars)

## Fetching users that have starred specific repos

The `stargazers` command fetches the users that have starred the specified repos.

    $ github-to-sqlite stargazers github.db simonw/datasette dogsheep/github-to-sqlite

You can specify one or more repository using `owner/repo` syntax.

Users fetched using this command will be inserted into the `users` table. Many-to-many records showing which repository they starred will be added to the `stars` table.

## Fetching GitHub Actions workflows

The `workflows` command fetches the YAML workflow configurations from each repository's `.github/workflows` directory and parses them to populate `workflows`, `jobs` and `steps` tables.

    $ github-to-sqlite workflows github.db simonw/datasette dogsheep/github-to-sqlite

You can specify one or more repository using `owner/repo` syntax.

Example: [workflows table](https://github-to-sqlite.dogsheep.net/github/workflows), [jobs table](https://github-to-sqlite.dogsheep.net/github/jobs), [steps table](https://github-to-sqlite.dogsheep.net/github/steps)

## Scraping dependents for a repository

The GitHub dependency graph can show other GitHub projects that depend on a specific repo, for example [simonw/datasette/network/dependents](https://github.com/simonw/datasette/network/dependents).

This data is not yet available through the GitHub API. The `scrape-dependents` command scrapes those pages and uses the GitHub API to load full versions of the dependent repositories.

    $ github-to-sqlite scrape-dependents github.db simonw/datasette

The command accepts one or more repositories.

Add `-v` for verbose output.

Example: [dependents table](https://github-to-sqlite.dogsheep.net/github/dependents)

## Fetching emojis

You can fetch a list of every emoji supported by GitHub using the `emojis` command:

    $ github-to-sqlite emojis github.db

This will create a table callad `emojis` with a primary key `name` and a `url` column.

If you add the `--fetch` option the command will also fetch the binary content of the images and place them in an `image` column:

    $ github-to-sqlite emojis emojis.db -f
    [########----------------------------]  397/1799   22%  00:03:43

You can then use the [datasette-render-images](https://github.com/simonw/datasette-render-images) plugin to browse them visually.

Example: [emojis table](https://github-to-sqlite.dogsheep.net/github/emojis)

## Making authenticated API calls

The `github-to-sqlite get` command provides a convenient shortcut for making authenticated calls to the API. Once you have created your `auth.json` file (or set a `GITHUB_TOKEN` environment variable) you can use it like this:

    $ github-to-sqlite get https://api.github.com/gists

This will make an authenticated call to the URL you provide and pretty-print the resulting JSON to the console.

You can ommit the `https://api.github.com/` prefix, for example:

    $ github-to-sqlite get /gists

Many GitHub APIs are [paginated using the HTTP Link header](https://docs.github.com/en/rest/guides/traversing-with-pagination). You can follow this pagination and output a list of all of the resulting items using `--paginate`:

    $ github-to-sqlite get /users/simonw/repos --paginate

You can outline newline-delimited JSON for each item using `--nl`. This can be useful for streaming items into another tool.

    $ github-to-sqlite get /users/simonw/repos --nl
