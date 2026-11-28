"""Message-mode boxes. EarlyReturns carrying plain data, not exceptions."""

from ruok import Err, catch, display_error, is_err


@display_error
def scenario_short() -> None:
  Err("Just a message to the user").q()


@display_error
def scenario_long() -> None:
  Err("VERY LONG " * 30).q()


@display_error
def scenario_multiline() -> None:
  Err("abc\nasdfa\n\nasdfasdfasdfasdf").q()


@catch
def _inner() -> None:
  Err("Just a message to the user. Nested").q()


@catch
def _outer() -> None:
  _inner().q()


@display_error(strip_early_returns=False)
def scenario_nested_unstripped() -> None:
  result = _outer()
  if is_err(result):
    raise result.err()
