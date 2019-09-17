# github-to-sqlite

[![PyPI](https://img.shields.io/pypi/v/github-to-sqlite.svg)](https://pypi.org/project/github-to-sqlite/)
[![CircleCI](https://circleci.com/gh/dogsheep/github-to-sqlite.svg?style=svg)](https://circleci.com/gh/dogsheep/github-to-sqlite)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/dogsheep/github-to-sqlite/blob/master/LICENSE)

Save data from GitHub to a SQLite database.

## How to install

    $ pip install github-to-sqlite

## Authentication

Create a GitHub personal access token: https://github.com/settings/tokens

Run this command and paste in your new token:

    $ github-to-sqlite auth

This will create a file called `auth.json` in your current directory containing the required value. To save the file at a different path or filename, use the `--auth=myauth.json` option.

## Retrieving issues for a repository

The `issues` command retrieves all of the issues belonging to a specified repository.

    $ github-to-sqlite issues github.db simonw/datasette

If an `auth.json` file is present it will use the token from that file. It works without authentication for public repositories but you should be aware that GitHub have strict IP-based rate limits for unauthenticated requests.

You can point to a different location of `auth.json` using `-a`:

    $ github-to-sqlite issues github.db simonw/datasette -a /path/to/auth.json

## Fetching repos belonging to a user or organization

The `repos` command fetches repos belonging to a user or organization.

Without any other arguments, this command will fetch all repos that the currently authenticated user owns, collaborates on or can access via one of their organizations:

    $ github-to-sqlite repos github.db

To fetch repos belonging to a specific user or organization, provide their username as an argument:

    $ github-to-sqlite repos github.db dogsheep # organization
    $ github-to-sqlite repos github.db simonw # user

## Fetching repos that have been starred by a user

The `starred` command fetches the repos that have been starred by a user.

    $ github-to-sqlite starred github.db simonw

If you are using an `auth.json` file you can omit the username to retrieve the starred repos for the authenticated user.
