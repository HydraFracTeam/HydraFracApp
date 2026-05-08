from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from PySide6.QtWidgets import QTextEdit


class ReportLevel(str, Enum):
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SOLVER = "SOLVER"


@dataclass(slots=True)
class ReportEntry:
    timestamp: datetime
    level: ReportLevel
    message: str


class ReportService:

    def __init__(self, text_widget: QTextEdit):
        self.text_widget = text_widget

    def info(self, message: str):
        self._append(
            ReportEntry(
                timestamp=datetime.now(),
                level=ReportLevel.INFO,
                message=message,
            )
        )

    def success(self, message: str):
        self._append(
            ReportEntry(
                timestamp=datetime.now(),
                level=ReportLevel.SUCCESS,
                message=message,
            )
        )

    def warning(self, message: str):
        self._append(
            ReportEntry(
                timestamp=datetime.now(),
                level=ReportLevel.WARNING,
                message=message,
            )
        )

    def error(self, message: str):
        self._append(
            ReportEntry(
                timestamp=datetime.now(),
                level=ReportLevel.ERROR,
                message=message,
            )
        )

    def solver(self, message: str):
        self._append(
            ReportEntry(
                timestamp=datetime.now(),
                level=ReportLevel.SOLVER,
                message=message,
            )
        )

    def clear(self):
        self.text_widget.clear()

    def _append(self, entry: ReportEntry):

        ts = entry.timestamp.strftime("%H:%M:%S")

        prefix = {
            ReportLevel.INFO: "[INFO]",
            ReportLevel.SUCCESS: "[ OK ]",
            ReportLevel.WARNING: "[WARN]",
            ReportLevel.ERROR: "[ERR ]",
            ReportLevel.SOLVER: "[SOLV]",
        }[entry.level]

        line = f"{ts} {prefix} {entry.message}"

        self.text_widget.append(line)
