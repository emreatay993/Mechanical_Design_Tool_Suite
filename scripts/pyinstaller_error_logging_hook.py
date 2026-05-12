"""Optional packaged-executable error logging for PyInstaller builds.

This runtime hook is loaded before the bundled entry script. It stays inactive
unless debug logging is requested by the build or by the launch environment.
"""

from __future__ import annotations

import atexit
import faulthandler
import logging
import os
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path
from types import TracebackType


_DEBUG_FLAG_FILE = "mdts_debug_build.flag"
_ENV_ENABLE_LOGS = "MDTS_PACKAGED_ERROR_LOGS"
_LOG_FILE_HANDLE = None
_FAULT_FILE_HANDLE = None


def _truthy(value: str | None) -> bool:
    return value is not None and value.strip().lower() in {"1", "true", "yes", "on"}


def _bundle_internal_dir() -> Path:
    internal_dir = getattr(sys, "_MEIPASS", None)
    if internal_dir:
        return Path(internal_dir)
    return Path(sys.executable).resolve().parent / "_internal"


def _logging_requested(internal_dir: Path) -> bool:
    return _truthy(os.environ.get(_ENV_ENABLE_LOGS)) or (internal_dir / _DEBUG_FLAG_FILE).exists()


class _TeeStream:
    def __init__(self, original, log_file) -> None:
        self._original = original
        self._log_file = log_file

    def write(self, text: str) -> int:
        if self._original is not None:
            try:
                self._original.write(text)
            except Exception:
                pass
        self._log_file.write(text)
        self._log_file.flush()
        return len(text)

    def flush(self) -> None:
        if self._original is not None:
            try:
                self._original.flush()
            except Exception:
                pass
        self._log_file.flush()

    def isatty(self) -> bool:
        return bool(self._original is not None and self._original.isatty())

    @property
    def encoding(self) -> str:
        return getattr(self._original, "encoding", "utf-8")

    @property
    def errors(self) -> str:
        return getattr(self._original, "errors", "replace")


def _format_exception(exc_type: type[BaseException], exc_value: BaseException, exc_tb: TracebackType | None) -> str:
    return "".join(traceback.format_exception(exc_type, exc_value, exc_tb))


def _install_error_logging() -> None:
    global _FAULT_FILE_HANDLE, _LOG_FILE_HANDLE

    if not getattr(sys, "frozen", False):
        return

    internal_dir = _bundle_internal_dir()
    if not _logging_requested(internal_dir):
        return

    internal_dir.mkdir(parents=True, exist_ok=True)
    exe_name = Path(sys.executable).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    process_id = os.getpid()
    log_path = internal_dir / f"{exe_name}_{timestamp}_{process_id}.log"
    fault_path = internal_dir / f"{exe_name}_{timestamp}_{process_id}_faults.log"

    _LOG_FILE_HANDLE = log_path.open("a", encoding="utf-8", buffering=1)
    _FAULT_FILE_HANDLE = fault_path.open("a", encoding="utf-8", buffering=1)

    sys.stdout = _TeeStream(sys.stdout, _LOG_FILE_HANDLE)
    sys.stderr = _TeeStream(sys.stderr, _LOG_FILE_HANDLE)

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
        force=True,
    )
    logging.captureWarnings(True)

    try:
        faulthandler.enable(file=_FAULT_FILE_HANDLE, all_threads=True)
    except Exception:
        logging.exception("Failed to enable faulthandler logging.")

    logging.info("Packaged debug logging enabled for %s", sys.executable)
    logging.info("Writing debug log to %s", log_path)
    logging.info("Writing faulthandler log to %s", fault_path)

    original_excepthook = sys.excepthook
    original_threading_excepthook = getattr(threading, "excepthook", None)
    original_unraisablehook = getattr(sys, "unraisablehook", None)

    def excepthook(exc_type, exc_value, exc_tb):
        logging.critical("Unhandled exception:\n%s", _format_exception(exc_type, exc_value, exc_tb))
        original_excepthook(exc_type, exc_value, exc_tb)

    def threading_excepthook(args):
        logging.critical(
            "Unhandled exception in thread %s:\n%s",
            args.thread.name if args.thread else "<unknown>",
            _format_exception(args.exc_type, args.exc_value, args.exc_traceback),
        )
        if original_threading_excepthook is not None:
            original_threading_excepthook(args)

    def unraisablehook(unraisable):
        logging.critical(
            "Unraisable exception in %r:\n%s",
            unraisable.object,
            _format_exception(unraisable.exc_type, unraisable.exc_value, unraisable.exc_traceback),
        )
        if original_unraisablehook is not None:
            original_unraisablehook(unraisable)

    sys.excepthook = excepthook
    threading.excepthook = threading_excepthook
    sys.unraisablehook = unraisablehook

    def close_logs() -> None:
        logging.info("Packaged executable is exiting.")
        for file_handle in (_FAULT_FILE_HANDLE, _LOG_FILE_HANDLE):
            if file_handle is not None:
                file_handle.flush()

    atexit.register(close_logs)


try:
    _install_error_logging()
except Exception:
    # Runtime hooks should never prevent a packaged app from starting.
    pass
