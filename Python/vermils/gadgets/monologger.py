# -*- coding: utf-8 -*-
from __future__ import annotations
import logging
import os
from weakref import WeakValueDictionary


class MonoLogger:
    """
    # MonoLogger: A logger that logs to separate files.
    """

    _logger_map = WeakValueDictionary[str, "MonoLogger"]()

    def __init__(
            self,
            name: str = "root",
            level: str | int = "WARNING",
            path: str | None = None,
            formatter: logging.Formatter | str | None = None,
    ):
        MonoLogger._logger_map[name] = self
        self._name = name
        if not path:  # pragma: no cover
            path = os.path.join(os.getcwd(), name + ".logs")
        self.path = path
        if not os.path.exists(path):
            os.makedirs(self.path, exist_ok=True)
        elif not os.path.isdir(self.path):
            raise ValueError("log path should be a directory")
        self._debug = logging.getLogger(self.name + "-debug")
        self._info = logging.getLogger(self.name + "-info")
        self._warning = logging.getLogger(self.name + "-warning")
        self._error = logging.getLogger(self.name + "-error")
        self._critical = logging.getLogger(self.name + "-critical")
        self.level = level

        self._debug_hdlr = logging.FileHandler(
            os.path.join(self.path, "debug.log"), mode='w', encoding="utf-8")
        self._debug.addHandler(self._debug_hdlr)
        self._info_hdlr = logging.FileHandler(
            os.path.join(self.path, "info.log"), mode='w', encoding="utf-8")
        self._info.addHandler(self._info_hdlr)
        self._warning_hdlr = logging.FileHandler(
            os.path.join(self.path, "warning.log"), mode='w', encoding="utf-8")
        self._warning.addHandler(self._warning_hdlr)
        self._error_hdlr = logging.FileHandler(
            os.path.join(self.path, "error.log"), mode='w', encoding="utf-8")
        self._error.addHandler(self._error_hdlr)
        self._critical_hdlr = logging.FileHandler(
            os.path.join(self.path, "critical.log"), mode='w', encoding="utf-8")
        self._critical.addHandler(self._critical_hdlr)
        self.formatter = formatter

    @property
    def name(self):
        return self._name

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, path: str):
        self._path = path

    @property
    def debug(self):
        return self._debug.debug

    @property
    def info(self):
        return self._info.info

    @property
    def warning(self):
        return self._warning.warning

    @property
    def error(self):
        return self._error.error

    @property
    def critical(self):
        return self._critical.critical

    def exception(self, msg: object, *args, **kw):
        if "exc_info" not in kw:
            kw["exc_info"] = msg
        return self._error.exception(msg, *args, **kw)

    def log(self, level: int, msg: object, *args, **kwargs):
        level = level
        match level:
            case logging.DEBUG:
                self._debug.log(level, msg, *args, **kwargs)
            case logging.INFO:
                self._info.log(level, msg, *args, **kwargs)
            case logging.WARNING:
                self._warning.log(level, msg, *args, **kwargs)
            case logging.ERROR:
                self._error.log(level, msg, *args, **kwargs)
            case logging.CRITICAL:
                self._critical.log(level, msg, *args, **kwargs)
            case _:
                raise ValueError("invalid log level")

    def addHandler(self, handler: logging.Handler):
        self._debug.addHandler(handler)
        self._info.addHandler(handler)
        self._warning.addHandler(handler)
        self._error.addHandler(handler)
        self._critical.addHandler(handler)

    def removeHandler(self, handler: logging.Handler):
        self._debug.removeHandler(handler)
        self._info.removeHandler(handler)
        self._warning.removeHandler(handler)
        self._error.removeHandler(handler)
        self._critical.removeHandler(handler)

    @property
    def formatter(self):
        return self._formatter

    @formatter.setter
    def formatter(self, formatter: logging.Formatter | str | None = None):
        if not formatter:
            formatter = logging.Formatter("%(asctime)s:  %(message)s")
        elif isinstance(formatter, str):
            formatter = logging.Formatter(formatter)
        self._formatter = formatter
        self._debug_hdlr.setFormatter(formatter)
        self._info_hdlr.setFormatter(formatter)
        self._warning_hdlr.setFormatter(formatter)
        self._error_hdlr.setFormatter(formatter)
        self._critical_hdlr.setFormatter(formatter)

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, level: str | int):
        level = str.upper(level) if isinstance(level, str) else level
        self._level = level
        self._debug.setLevel(level)
        self._info.setLevel(level)
        self._warning.setLevel(level)
        self._error.setLevel(level)
        self._critical.setLevel(level)

    @classmethod
    def getLogger(cls, name: str) -> MonoLogger | None:
        """Get a logger by name, if not exist, return `None`"""
        if name in cls._logger_map:
            return cls._logger_map[name]
        return None
