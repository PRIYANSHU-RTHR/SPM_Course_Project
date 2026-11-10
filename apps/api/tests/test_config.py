from pathlib import Path

from app.config import _repo_root_env


def test_repo_root_env_is_three_levels_above_app() -> None:
    config = Path("/home/dev/orchestrai/apps/api/app/config.py")
    assert _repo_root_env(config) == Path("/home/dev/orchestrai/.env")


def test_shallow_install_has_no_repo_env_instead_of_crashing() -> None:
    # e.g. the code mounted at /src in a container: /src/app/config.py has only 3 parents.
    assert _repo_root_env(Path("/src/app/config.py")) is None
