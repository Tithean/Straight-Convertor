import logging
import shutil
import tempfile
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def create_workspace(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="conversion-", dir=root)).resolve()


def remove_workspace(workspace: Path) -> None:
    try:
        shutil.rmtree(workspace)
    except FileNotFoundError:
        pass
    except OSError:
        logger.warning(
            "Temporary workspace cleanup failed; startup cleanup will retry."
        )


def remove_stale_workspaces(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for workspace in root.glob("conversion-*"):
        if (
            workspace.is_dir()
            and not workspace.is_symlink()
            and time.time() - workspace.stat().st_mtime > 86400
        ):
            remove_workspace(workspace)
