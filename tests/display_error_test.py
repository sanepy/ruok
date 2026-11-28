import json
from collections.abc import Callable, Sequence
from types import TracebackType

import pytest

from ruok import RE, EarlyReturn, Err, catch, display_error, is_err


def _noop_displayer(_exc: Exception) -> None:
  """Suppress terminal output during tests."""


def _capture_exception(
  body: Callable[[], None], *, strip_early_returns: bool = True
) -> BaseException:
  """Run body inside a @catch'd function under display_error and return the
  single exception the handler receives."""
  captured: list[BaseException] = []

  @display_error(
    handler=captured.append,
    displayer=_noop_displayer,
    strip_early_returns=strip_early_returns,
  )
  def main():
    @catch
    def inner() -> None:
      body()

    result: RE[None] = inner()
    if is_err(result):
      raise result.err()

  with pytest.raises(SystemExit):
    main()

  assert len(captured) == 1
  return captured[0]


class TestStripEarlyReturns:
  """Tests that display_error correctly strips EarlyReturn wrappers."""

  def test_string_err_is_stripped(self):
    """Err("msg").q() should strip the EarlyReturn, preserving the message."""

    def body() -> None:
      Err("connection failed").q()

    exc = _capture_exception(body)
    assert isinstance(exc, EarlyReturn)
    assert exc.args[0] == "connection failed"

  def test_exception_err_is_stripped_to_cause(self):
    """Err(ValueError(...)).q() should strip EarlyReturn down to the ValueError."""

    def body() -> None:
      Err(ValueError("bad value")).q()

    exc = _capture_exception(body)
    assert isinstance(exc, ValueError)
    assert str(exc) == "bad value"

  def test_nested_early_returns_fully_stripped(self):
    """Chained EarlyReturns from nested @catch should strip down to the root cause."""

    def body() -> None:
      @catch
      def level2() -> None:
        Err(ValueError("root")).q()

      @catch
      def level1() -> None:
        # level2's result is Err(EarlyReturn(ValueError("root"))), and the
        # .q() below wraps it in a second EarlyReturn.
        level2().q()

      level1().q()

    exc = _capture_exception(body)
    assert isinstance(exc, ValueError)
    assert str(exc) == "root"

  def test_string_err_preserves_hops(self, monkeypatch: pytest.MonkeyPatch):
    """Err("msg").q() should preserve hops."""
    calls: list[tuple[BaseException, Sequence[TracebackType]]] = []

    def spy(
      exc: BaseException,
      hops: Sequence[TracebackType] = (),
      **_kwargs: object,
    ) -> None:
      calls.append((exc, hops))

    monkeypatch.setattr("ruok.ruok.error_displayer", spy)

    @display_error(strip_early_returns=True)
    def main():
      @catch
      def inner() -> None:
        Err("lost hops").q()

      result: RE[None] = inner()
      if is_err(result):
        raise result.err()

    with pytest.raises(SystemExit):
      main()

    assert len(calls) == 1
    exc, hops = calls[0]
    assert isinstance(exc, EarlyReturn)
    assert exc.args[0] == "lost hops"
    assert len(hops) > 0

  def test_strip_disabled_passes_raw_early_return(self):
    """With strip_early_returns=False, handler receives the raw EarlyReturn."""

    def body() -> None:
      Err(ValueError("inner")).q()

    exc = _capture_exception(body, strip_early_returns=False)
    assert isinstance(exc, EarlyReturn)


class TestKeyboardInterrupt:
  def test_caught_exits_130(self):
    @display_error
    def main() -> None:
      raise KeyboardInterrupt

    with pytest.raises(SystemExit) as exc_info:
      main()

    assert exc_info.value.code == 130

  def test_caught_skips_handler_and_displayer(self):
    calls: list[Exception] = []

    @display_error(handler=calls.append, displayer=_noop_displayer)
    def main() -> None:
      raise KeyboardInterrupt

    with pytest.raises(SystemExit):
      main()

    assert calls == []

  def test_opt_out_propagates(self):
    @display_error(catch_keyboard_interrupt=False)
    def main() -> None:
      raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
      main()

  def test_pierced_via_err_q_exits_130(self):
    @display_error
    def main() -> None:
      Err(KeyboardInterrupt("kbd")).q()

    with pytest.raises(SystemExit) as exc_info:
      main()

    assert exc_info.value.code == 130


class TestHandRaisedEarlyReturn:
  """Hand-raised EarlyReturns wrapping non-Exception payloads are not
  pierced; they surface as ordinary exceptions."""

  def test_early_return_wrapping_keyboard_interrupt(self):
    captured: list[Exception] = []

    @display_error(handler=captured.append, displayer=_noop_displayer)
    def main() -> None:
      raise EarlyReturn(KeyboardInterrupt(ValueError("abc")))

    with pytest.raises(SystemExit) as exc_info:
      main()

    assert exc_info.value.code == 1
    assert len(captured) == 1
    assert isinstance(captured[0], EarlyReturn)
    assert isinstance(captured[0].args[0], KeyboardInterrupt)


class TestEarlyReturnAsMessage:
  """A bare EarlyReturn with a non-exception payload renders as a plain
  message box: no error type, no location, no code snippet."""

  def test_direct_raise_renders_message_only(self, capsys: pytest.CaptureFixture[str]):
    @display_error
    def main() -> None:
      raise EarlyReturn("Set this in the env var")

    with pytest.raises(SystemExit):
      main()

    out = capsys.readouterr()
    assert "Set this in the env var" in out.err
    assert "[EarlyReturn]" not in out.err
    assert "caused by:" not in out.err

  def test_via_err_q_renders_message_only(self, capsys: pytest.CaptureFixture[str]):
    @display_error
    def main() -> None:
      @catch
      def inner() -> None:
        Err("Set this in the env var").q()

      result: RE[None] = inner()
      result.q()

    with pytest.raises(SystemExit):
      main()

    out = capsys.readouterr()
    assert "Set this in the env var" in out.err
    assert "[EarlyReturn]" not in out.err

  def test_with_cause_still_renders_full_error(
    self, capsys: pytest.CaptureFixture[str]
  ):
    @display_error
    def main() -> None:
      raise EarlyReturn("failed") from ValueError("root cause")

    with pytest.raises(SystemExit):
      main()

    out = capsys.readouterr()
    assert "[ValueError]" in out.err
    assert "root cause" in out.err

  def test_exception_payload_still_renders_full_error(
    self, capsys: pytest.CaptureFixture[str]
  ):
    @display_error
    def main() -> None:
      raise EarlyReturn(ValueError("real error"))

    with pytest.raises(SystemExit):
      main()

    out = capsys.readouterr()
    assert "[ValueError]" in out.err

  def test_from_none_renders_message(self, capsys: pytest.CaptureFixture[str]):
    """`from None` explicitly suppresses the cause, so the author's intent
    is a message, not an error."""

    @display_error
    def run() -> None:
      try:
        raise ValueError("root cause")  # noqa: TRY301
      except ValueError:
        raise EarlyReturn("failed") from None

    with pytest.raises(SystemExit):
      run()

    out = capsys.readouterr()
    assert "failed" in out.err
    assert "[ValueError]" not in out.err

  def test_raised_inside_except_without_from_still_renders_full_error(
    self, capsys: pytest.CaptureFixture[str]
  ):
    """An implicit __context__ means a real error is being handled —
    it must not be shadowed by the message."""

    @display_error
    def run() -> None:
      try:
        raise ValueError("root cause")  # noqa: TRY301
      except ValueError:
        raise EarlyReturn("failed")  # noqa: B904

    with pytest.raises(SystemExit):
      run()

    out = capsys.readouterr()
    assert "[ValueError]" in out.err
    assert "root cause" in out.err

  def test_nested_message_renders_message_only(
    self, capsys: pytest.CaptureFixture[str]
  ):
    """A message .q()'d through multiple catches still renders as a plain
    message box when strip_early_returns=False: the extra layers are just
    propagation hops."""

    @display_error(strip_early_returns=False)
    def main() -> None:
      @catch
      def level2() -> None:
        Err("just a message").q()

      @catch
      def level1() -> None:
        level2().q()

      result = level1()
      if isinstance(result, Err):
        raise result.err()

    with pytest.raises(SystemExit):
      main()

    out = capsys.readouterr().err
    assert "just a message" in out
    assert "[EarlyReturn]" not in out
    assert "caused by:" not in out

  def test_nested_message_with_implicit_context_renders_full_error(
    self, capsys: pytest.CaptureFixture[str]
  ):
    """An implicit __context__ at any layer means a real error was being
    handled. It must not be shadowed by the message."""

    @display_error(strip_early_returns=False)
    def main() -> None:
      @catch
      def level2() -> None:
        try:
          raise ValueError("root cause")  # noqa: TRY301
        except ValueError:
          raise EarlyReturn("failed")  # noqa: B904

      @catch
      def level1() -> None:
        level2().q()

      result = level1()
      if isinstance(result, Err):
        raise result.err()

    with pytest.raises(SystemExit):
      main()

    out = capsys.readouterr().err
    assert "[ValueError]" in out
    assert "root cause" in out


class TestInternalFrames:
  """Frames inside ruok itself must never be picked as the error location;
  neither when ruok is installed (site-packages filter) nor when imported from
  a source checkout (own-package filter)."""

  def test_ruok_internal_frames_not_shown(self, capsys: pytest.CaptureFixture[str]):
    @display_error(strip_early_returns=False)
    def main() -> None:
      @catch
      def inner() -> None:
        Err(ValueError("boom")).q()

      result = inner()
      if isinstance(result, Err):
        raise result.err()

    with pytest.raises(SystemExit):
      main()

    out = capsys.readouterr().err
    assert "ruok.py" not in out
    assert "inner()" in out

  def test_stdlib_frames_not_shown(self, capsys: pytest.CaptureFixture[str]):
    """json.loads raises deep inside json/decoder.py, but the panel must
    point at the user frame that called into the stdlib."""

    @display_error
    def main() -> None:
      json.loads("invalid")

    with pytest.raises(SystemExit):
      main()

    out = capsys.readouterr().err
    assert "decoder.py" not in out
    assert "json.loads" in out


class TestBorder:
  def test_disabled_renders_bare(self, capsys: pytest.CaptureFixture[str]):
    @display_error(border=False)
    def main() -> None:
      raise ValueError("oops")

    with pytest.raises(SystemExit):
      main()

    out = capsys.readouterr()
    assert "oops [ValueError]" in out.err
    assert "\u256e" not in out.err  # panel corner (╮)
    assert "\u256f" not in out.err  # panel corner (╯)
