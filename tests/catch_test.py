import pytest

from ruok import EarlyReturn, Err, Ok, catch


class TestCatchNoArgs:
  def test_plain_return_wrapped_in_ok(self):
    @catch
    def f() -> int:
      return 42

    assert f() == Ok(42)

  def test_none_return_wrapped_in_ok(self):
    @catch
    def f() -> None:
      pass

    assert f() == Ok(None)

  def test_raised_exception_wrapped_in_err(self):
    @catch
    def f():
      raise ValueError("oops")

    result = f()
    assert isinstance(result, Err)
    assert isinstance(result.err(), ValueError)
    assert str(result.err()) == "oops"

  def test_does_not_catch_base_exception(self):
    @catch
    def f():
      raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
      _ = f()

  def test_ok_q_extracts_value_and_continues(self):
    @catch
    def f() -> int:
      v = Ok(7).q()
      return v + 1

    assert f() == Ok(8)

  def test_multiple_ok_q_calls(self):
    @catch
    def f() -> int:
      a = Ok(1).q()
      b = Ok(2).q()
      return a + b

    assert f() == Ok(3)

  def test_err_q_raises_early_return_which_is_caught(self):
    @catch
    def f():
      Err("fail").q()

    result = f()
    assert isinstance(result, Err)
    early = result.err()
    assert isinstance(early, EarlyReturn)
    assert early.args[0] == "fail"

  def test_err_q_non_exception_value_has_no_cause(self):
    @catch
    def f():
      Err("plain").q()

    result = f()
    assert isinstance(result, Err)
    assert result.err().__cause__ is None

  def test_err_q_exception_value_chained_as_cause(self):
    inner = ValueError("root")

    @catch
    def f():
      Err(inner).q()

    result = f()
    assert isinstance(result, Err)
    early = result.err()
    assert isinstance(early, EarlyReturn)
    assert early.args[0] is inner
    assert early.__cause__ is inner

  def test_err_q_stops_execution_immediately(self):
    calls: list[str] = []

    @catch
    def f():
      Err("stop").q()
      calls.append("unreachable")  # pyright: ignore[reportUnreachable]

    _ = f()
    assert calls == []


class TestCatchWithExceptionTypes:
  def test_catches_specified_exception(self):
    @catch(ValueError)
    def f():
      raise ValueError("val")

    result = f()
    assert isinstance(result, Err)
    assert isinstance(result.err(), ValueError)

  def test_does_not_catch_unspecified_exception(self):
    @catch(ValueError)
    def f():
      raise TypeError("nope")

    with pytest.raises(TypeError):
      _ = f()

  def test_catches_multiple_exception_types(self):
    @catch(ValueError, TypeError)
    def f(which: str):
      if which == "v":
        raise ValueError
      raise TypeError

    err_value_err = f("v")
    assert isinstance(err_value_err, Err)
    assert isinstance(err_value_err.err(), ValueError)
    err_type_err = f("t")
    assert isinstance(err_type_err, Err)
    assert isinstance(err_type_err.err(), TypeError)

  def test_empty_call_catches_all_exceptions(self):
    @catch()
    def f():
      raise RuntimeError("boom")

    result = f()
    assert isinstance(result, Err)
    assert isinstance(result.err(), RuntimeError)

  def test_early_return_not_caught_when_not_in_specified_types(self):
    @catch(ValueError)
    def f():
      Err("escape").q()

    with pytest.raises(EarlyReturn) as exc_info:
      _ = f()

    assert exc_info.value.args[0] == "escape"

  def test_early_return_cause_preserved_when_escaping(self):
    inner = ValueError("chained")

    @catch(TypeError)
    def f():
      Err(inner).q()

    with pytest.raises(EarlyReturn) as exc_info:
      _ = f()

    assert exc_info.value.__cause__ is inner


class TestCatchMetadata:
  def test_preserves_name(self):
    @catch
    def my_fn():
      return 1

    assert my_fn.__name__ == "my_fn"

  def test_preserves_docstring(self):
    @catch
    def f():
      """My doc."""
      return 1

    assert f.__doc__ == "My doc."

  def test_preserves_module(self):
    @catch
    def f():
      return 1

    assert f.__module__ == __name__


class TestCatchArguments:
  def test_positional_and_keyword_args(self):
    @catch
    def f(a: int, b: int = 10) -> int:
      return a + b

    assert f(5) == Ok(15)
    assert f(5, b=3) == Ok(8)

  def test_exception_varies_by_arg(self):
    @catch
    def f(x: int):
      if x < 0:
        raise ValueError(f"negative: {x}")
      return x

    assert f(5) == Ok(5)
    result = f(-1)
    assert isinstance(result, Err)
    assert isinstance(result.err(), ValueError)


class TestCatchNested:
  def test_inner_err_q_does_not_leak_through_outer(self):
    @catch
    def inner() -> int:
      Err("inner error").q()

    @catch
    def outer():
      result = inner()
      assert isinstance(result, Err)
      assert isinstance(result.err(), EarlyReturn)
      return "ok"

    assert outer() == Ok("ok")
