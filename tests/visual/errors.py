"""Full exception panels: headers, locations, snippets, cause chains."""

from ruok import Err, catch, display_error, is_err


@display_error
def scenario_simple() -> None:
  raise ValueError("Something went wrong")


@display_error
def scenario_long_message() -> None:
  raise ValueError("VERY LONG " * 30)


@display_error(border=False)
def scenario_no_border() -> None:
  raise ValueError("Something went wrong without a border")


@display_error
def scenario_long_source_line() -> None:
  # Intentionally long line. Intentionally long line. Intentionally long line. Intentionally long line. Intentionally long line. Intentionally long line. Intentionally long line. Intentionally long line. Intentionally long line. # noqa: E501
  raise ValueError("Short message")


def _connect() -> None:
  raise ConnectionError("Database connection failed")


@display_error(show_propagation=True)
def scenario_chain() -> None:
  try:
    _connect()
  except ConnectionError as exc:
    Err(exc).q()


@catch
def _boom_inner() -> None:
  raise ValueError("Kaboom")


@catch
def _boom_outer() -> None:
  result = _boom_inner()
  if is_err(result):
    Err(result.err()).q()


@display_error(show_propagation=True)
def scenario_nested_error() -> None:
  result = _boom_outer()
  if is_err(result):
    raise result.err()
