from gitbark.util import cmd as _cmd
from gitbark.objects import BarkRules
from gitbark.core import BARK_RULES, BARK_RULES_BRANCH
from gitbark.git import BARK_CONFIG, COMMIT_RULES

from typing import Any
from dataclasses import asdict
from contextlib import contextmanager

import os
import shutil
import stat
import yaml

MAIN_BRANCH = "main"


class Repo:
    def __init__(self, path: str) -> None:
        self.path = path
        if not os.path.exists(self.path):
            os.makedirs(self.path)

        self.init_repo()
        self.init_config()

    def cmd(self, *cmd: str, check: bool = True, **kwargs: Any):
        return _cmd(*cmd, check=check, cwd=self.path, **kwargs)

    @property
    def head(self) -> str:
        """Returns the commit the HEAD points to."""
        return self.cmd("git", "rev-parse", "HEAD")[0]

    @property
    def active_branch(self) -> str:
        """Returns the active branch."""
        return self.cmd("git", "symbolic-ref", "--short", "HEAD")[0]

    def init_repo(self) -> None:
        """Initializes git in repo."""
        self.cmd("git", "init")
        self.cmd("git", "checkout", "-b", MAIN_BRANCH)

    def init_config(self) -> None:
        self.cmd("git", "config", "commit.gpgsign", "false")
        self.set_user("Test", "test@test.com")
        # TODO any other configs we want to disable?

    def set_user(self, name: str, email: str) -> None:
        self.cmd("git", "config", "user.name", name)
        self.cmd("git", "config", "user.email", email)

    def has_branch(self, branch: str) -> bool:
        """Checks if a branch exists."""
        _, exit_code = self.cmd("git", "show-ref", "-q", "--heads", branch, check=False)
        if exit_code == 0:
            return True
        return False

    def checkout(self, branch: str, orphan: bool = False) -> None:
        """Checkouts a branch.

        If a branch does not exist it will be created.
        """
        if not self.has_branch(branch):
            if orphan:
                self.cmd("git", "checkout", "--orphan", branch)
            else:
                self.cmd("git", "checkout", "-b", branch)
        else:
            self.cmd("git", "checkout", branch)

    def commit(self, message: str = "Default msg", *options: str):
        self.cmd("git", "commit", "-m", message, "--allow-empty", *options)

    def write_bark_file(self, file: str, content: str) -> None:
        """Write and stage a bark file."""
        bark_folder = f"{self.path}/{BARK_CONFIG}"
        if not os.path.exists(bark_folder):
            os.mkdir(bark_folder)

        with open(file, "w") as f:
            f.write(content)

        self.cmd("git", "add", file)

    def write_bark_rules(self, bark_rules: BarkRules) -> None:
        """Write and stage bark rules."""
        if self.active_branch != BARK_RULES_BRANCH:
            raise Exception(
                f"Bark Rules should be created in the '{BARK_RULES_BRANCH}' branch!"
            )
        self.write_bark_file(
            file=f"{self.path}/{BARK_RULES}",
            content=yaml.safe_dump(asdict(bark_rules), sort_keys=False),
        )

    def write_commit_rules(self, commit_rules: dict) -> None:
        """Write and stage commit rules."""
        self.write_bark_file(
            file=f"{self.path}/{COMMIT_RULES}",
            content=yaml.safe_dump(commit_rules, sort_keys=False),
        )

    @contextmanager
    def on_branch(self, branch: str, orphan_branch: bool = False):
        curr_branch = self.active_branch
        try:
            self.checkout(branch, orphan_branch)
            yield self
        finally:
            self.checkout(curr_branch)

    def dump(self, dump_path: str) -> None:
        shutil.copytree(self.path, dump_path, dirs_exist_ok=True)

    def restore_from_dump(self, dump_path: str) -> None:
        # Recreating the folders to ensure all files and folders are copied.
        shutil.rmtree(self.path)
        shutil.copytree(dump_path, self.path)


@contextmanager
def uninstall_hooks(repo: Repo):
    hook_path = os.path.join(repo.path, ".git", "hooks", "reference-transaction")
    hook_content = None
    if os.path.exists(hook_path):
        with open(hook_path, "r") as f:
            hook_content = f.read()
        os.remove(hook_path)
    try:
        yield repo
    finally:
        if hook_content:
            with open(hook_path, "w") as f:
                f.write(hook_content)

            # Update permissions
            current_permissions = os.stat(hook_path).st_mode
            new_permissions = (
                current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            )
            os.chmod(hook_path, new_permissions)
