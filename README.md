# github-to-sqlite

[![PyPI](https://img.shields.io/pypi/v/github-to-sqlite.svg)](https://pypi.org/project/github-to-sqlite/)
[![CircleCI](https://circleci.com/gh/dogsheep/github-to-sqlite.svg?style=svg)](https://circleci.com/gh/dogsheep/github-to-sqlite)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/dogsheep/github-to-sqlite/blob/master/LICENSE)

Save data from GitHub to a SQLite database.

## Demo

https://github-to-sqlite.dogsheep.net/ hosts a [Datasette](https://datasette.readthedocs.io/) demo of a database created by [running this tool](https://github.com/dogsheep/github-to-sqlite/blob/471cf4f045d25bc319d61b9de3a698beaf1a6c96/.github/workflows/deploy-demo.yml#L40-L60) against all of the repositories in the [Dogsheep GitHub organization](https://github.com/dogsheep).

## How to install

    $ pip install github-to-sqlite

## Authentication

Create a GitHub personal access token: https://github.com/settings/tokens

Run this command and paste in your new token:

    $ github-to-sqlite auth

This will create a file called `auth.json` in your current directory containing the required value. To save the file at a different path or filename, use the `--auth=myauth.json` option.

## Fetching issues for a repository

The `issues` command retrieves all of the issues belonging to a specified repository.

    $ github-to-sqlite issues github.db simonw/datasette

If an `auth.json` file is present it will use the token from that file. It works without authentication for public repositories but you should be aware that GitHub have strict IP-based rate limits for unauthenticated requests.

You can point to a different location of `auth.json` using `-a`:

    $ github-to-sqlite issues github.db simonw/datasette -a /path/to/auth.json

You can use the `--issue` option to only load just one specific issue:

    $ github-to-sqlite issues github.db simonw/datasette --issue=1

## Fetching issue comments for a repository

The `issue-comments` command retrieves all of the comments on all of the issues in a repository.

It is recommended you run `issues` first, so that each imported comment can have a foreign key poining to its issue.

    $ github-to-sqlite issues github.db simonw/datasette
    $ github-to-sqlite issue-comments github.db simonw/datasette

You can use the `--issue` option to only load comments for a specific issue within that repository, for example:

    $ github-to-sqlite issue-comments github.db simonw/datasette --issue=1

## Fetching commits for a repository

The `commits` command retrieves details of all of the commits for one or more repositories. It currently fetches the sha, commit message and author and committer details - it does no retrieve the full commit body.

    $ github-to-sqlite commits github.db simonw/datasette simonw/sqlite-utils

The command accepts one or more repositories.

By default it will stop as soon as it sees a commit that has previously been retrieved. You can force it to retrieve all commits (including those that have been previously inserted) using `--all`.

## Fetching contributors to a repository

The `contributors` command retrieves details of all of the contributors for one or more repositories.

    $ github-to-sqlite contributors github.db simonw/datasette simonw/sqlite-utils

The command accepts one or more repositories. It populates a `contributors` table, with foreign keys to `repos` and `users` and a `contributions` table listing the number of commits to that repository for each contributor.

## Fetching repos belonging to a user or organization

The `repos` command fetches repos belonging to a user or organization.

Without any other arguments, this command will fetch all repos that the currently authenticated user owns, collaborates on or can access via one of their organizations:

    $ github-to-sqlite repos github.db

To fetch repos belonging to a specific user or organization, provide their username as an argument:

    $ github-to-sqlite repos github.db dogsheep # organization
    $ github-to-sqlite repos github.db simonw # user

You can pass more than one username to fetch for multiple users or organizations at once:

    $ github-to-sqlite repos github.db simonw dogsheep

## Fetching repos that have been starred by a user

The `starred` command fetches the repos that have been starred by a user.

    $ github-to-sqlite starred github.db simonw

If you are using an `auth.json` file you can omit the username to retrieve the starred repos for the authenticated user.
