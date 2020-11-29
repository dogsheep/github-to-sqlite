from github_to_sqlite import utils
import json
import pathlib
import pytest
import sqlite_utils
from sqlite_utils.db import ForeignKey


@pytest.fixture
def repo():
    return json.load(open(pathlib.Path(__file__).parent / "repo.json"))


@pytest.fixture
def workflow_yaml():
    return (pathlib.Path(__file__).parent / "deploy_demo.yml").read_text()


@pytest.fixture
def db(workflow_yaml, repo):
    db = sqlite_utils.Database(memory=True)
    utils.save_repo(db, repo)
    utils.save_workflow(db, repo["id"], "deploy_demo.yml", workflow_yaml)
    utils.ensure_db_shape(db)
    return db


def test_tables(db):
    assert {"repos", "workflows", "jobs", "steps"}.issubset(db.table_names())


def test_workflows(db):
    workflows = list(db["workflows"].rows)
    assert workflows == [
        {
            "id": 1,
            "filename": "deploy_demo.yml",
            "name": "Build and deploy demo",
            "on": '{"repository_dispatch": null, "push": {"branches": ["main"]}, "schedule": [{"cron": "0 0 * * *"}]}',
            "repo": 207052882,
        }
    ]


def test_jobs(db):
    jobs = list(db["jobs"].rows)
    assert jobs == [
        {
            "id": 1,
            "workflow": 1,
            "name": "scheduled",
            "repo": 207052882,
            "runs-on": "ubuntu-latest",
        }
    ]


def test_steps(db):
    steps = list(db["steps"].rows)
    assert steps == [
        {
            "id": 1,
            "seq": 1,
            "job": 1,
            "repo": 207052882,
            "uses": "actions/checkout@v2",
            "name": "Check out repo",
            "with": None,
            "run": None,
            "env": None,
        },
        {
            "id": 2,
            "seq": 2,
            "job": 1,
            "repo": 207052882,
            "uses": "actions/setup-python@v2",
            "name": "Set up Python",
            "with": '{"python-version": 3.8}',
            "run": None,
            "env": None,
        },
        {
            "id": 3,
            "seq": 3,
            "job": 1,
            "repo": 207052882,
            "uses": "actions/cache@v1",
            "name": "Configure pip caching",
            "with": '{"path": "~/.cache/pip", "key": "${{ runner.os }}-pip-${{ hashFiles(\'**/setup.py\') }}", "restore-keys": "${{ runner.os }}-pip-\\n"}',
            "run": None,
            "env": None,
        },
        {
            "id": 4,
            "seq": 4,
            "job": 1,
            "repo": 207052882,
            "uses": None,
            "name": "Install Python dependencies",
            "with": None,
            "run": "pip install -e .\n",
            "env": None,
        },
        {
            "id": 5,
            "seq": 5,
            "job": 1,
            "repo": 207052882,
            "uses": None,
            "name": "Create auth.json",
            "with": None,
            "run": 'echo "{\\"github_personal_token\\": \\"$GITHUB_ACCESS_TOKEN\\"}" > auth.json\n',
            "env": '{"GITHUB_ACCESS_TOKEN": "${{ secrets.GITHUB_ACCESS_TOKEN }}"}',
        },
        {
            "id": 6,
            "seq": 6,
            "job": 1,
            "repo": 207052882,
            "uses": "actions/upload-artifact@v2",
            "name": None,
            "with": '{"path": "github.db"}',
            "run": None,
            "env": None,
        },
        {
            "id": 7,
            "seq": 7,
            "job": 1,
            "repo": 207052882,
            "uses": "GoogleCloudPlatform/github-actions/setup-gcloud@master",
            "name": "Set up Cloud Run",
            "with": '{"version": "275.0.0", "service_account_email": "${{ secrets.GCP_SA_EMAIL }}", "service_account_key": "${{ secrets.GCP_SA_KEY }}"}',
            "run": None,
            "env": None,
        },
        {
            "id": 8,
            "seq": 8,
            "job": 1,
            "repo": 207052882,
            "uses": None,
            "name": "Deploy to Cloud Run",
            "with": None,
            "run": "gcloud config set run/region us-central1\ngcloud config set project datasette-222320\ndatasette publish cloudrun github.db",
            "env": None,
        },
    ]
