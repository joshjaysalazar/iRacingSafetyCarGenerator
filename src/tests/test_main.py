import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

import main

SRC_DIR = Path(__file__).resolve().parents[1]


def test_logging_config_writes_every_record_once(tmp_path):
    """Configured loggers log at their own level, other loggers under our packages at INFO, and
    everything else (third-party libraries) at WARNING, without duplicates.

    Runs in a subprocess because applying logging.json reconfigures the global root logger.
    """
    shutil.copy(SRC_DIR / "logging.json", tmp_path / "logging.json")
    script = textwrap.dedent(f"""
        import logging, sys
        sys.path.insert(0, {str(SRC_DIR)!r})
        from main import setup_logging
        setup_logging()
        logging.getLogger("core.generator").info("generator-info")
        logging.getLogger("core.generator").debug("generator-debug")
        logging.getLogger("core.preflight").info("preflight-info")
        logging.getLogger("core.new_module").info("new-core-module-info")
        logging.getLogger("core.new_module").debug("new-core-module-debug")
        logging.getLogger("util.new_module").info("new-util-module-info")
        logging.getLogger("some.library").warning("library-warning")
        logging.getLogger("some.library").info("library-info")
        try:
            raise RuntimeError("fatal")
        except RuntimeError:
            logging.exception("root-exception")
    """)

    subprocess.run([sys.executable, "-c", script], cwd=tmp_path, check=True)

    log = next((tmp_path / "logs").glob("*.log")).read_text()
    assert log.count("generator-info") == 1
    assert log.count("generator-debug") == 0
    assert log.count("preflight-info") == 1
    assert log.count("new-core-module-info") == 1
    assert log.count("new-core-module-debug") == 0
    assert log.count("new-util-module-info") == 1
    assert log.count("library-warning") == 1
    assert log.count("library-info") == 0
    assert log.count("root-exception") == 1
    assert "RuntimeError: fatal" in log


def test_fatal_startup_error_is_shown_to_the_user(mocker):
    mocker.patch.object(main, "setup_logging")
    mocker.patch.object(main, "App", side_effect=RuntimeError("broken settings"))
    showerror = mocker.patch("tkinter.messagebox.showerror")

    with pytest.raises(RuntimeError):
        main.main(arguments=None)

    showerror.assert_called_once()
    assert "broken settings" in showerror.call_args.args[1]
