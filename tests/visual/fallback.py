"""Fallback rendering when a custom handler or displayer crashes."""

from ruok import display_error


def _bad_handler(_exc: BaseException) -> None:
  raise RuntimeError("Handler crashed")


def _connect_to_log_server() -> None:
  raise ConnectionError("Connecting to log server")


def _bad_handler_with_cause(_exc: BaseException) -> None:
  try:
    _connect_to_log_server()
  except ConnectionError as conn_exc:
    raise RuntimeError("Handler crashed while logging") from conn_exc


def _bad_displayer(_exc: BaseException) -> None:
  raise TypeError("Displayer crashed")


@display_error(handler=_bad_handler)
def scenario_handler_fails() -> None:
  raise ValueError("Original error")


@display_error(handler=_bad_handler_with_cause)
def scenario_handler_fails_with_cause() -> None:
  raise ValueError("Original error")


@display_error(handler=_bad_handler, displayer=_bad_displayer)
def scenario_both_fail() -> None:
  raise ValueError("Original error")
