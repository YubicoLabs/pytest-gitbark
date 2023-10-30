from gitbark.cli.__main__ import cli, _DefaultFormatter
from gitbark.cli.util import CliFail

from .util import Repo

from click.testing import CliRunner

import logging
import pytest


@pytest.fixture(scope="session")
def bark_cli():
    return _bark_cli


def _bark_cli(*argv, **kwargs):
    handler = logging.StreamHandler()
    handler.setLevel(logging.WARNING)
    handler.setFormatter(_DefaultFormatter())
    logging.getLogger().addHandler(handler)

    runner = CliRunner(mix_stderr=True)
    result = runner.invoke(cli, argv, obj={}, **kwargs)
    if result.exit_code != 0:
        if isinstance(result.exception, CliFail):
            raise SystemExit()
        raise result.exception
    return result


@pytest.fixture(scope="session")
def repo_dump(tmp_path_factory):
    repo_path = tmp_path_factory.mktemp("repo")
    dump_path = tmp_path_factory.mktemp("dump")

    repo = Repo(repo_path)

    repo.dump(dump_path)
    return repo, dump_path


@pytest.fixture(scope="function")
def repo(repo_dump: tuple[Repo, str]):
    repo, dump_path = repo_dump
    repo.restore_from_dump(dump_path)
    return repo
