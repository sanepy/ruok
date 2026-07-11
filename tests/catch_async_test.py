import asyncio

import pytest

from ruok import EarlyReturn, Err, Ok, catch_async


class TestCatchAsyncNoArgs:
  """@catch_async used directly - catches all Exception subclasses."""

  async def test_successful_return_wrapped_in_ok(self):
    @catch_async
    async def f() -> int:
      return 123

    assert await f() == Ok(123)

  async def test_none_return_wrapped_in_ok(self):
    @catch_async
    async def f() -> None:
      pass

    assert await f() == Ok(None)

  async def test_raised_exception_wrapped_in_err(self):
    @catch_async
    async def f():
      raise ValueError("oops")

    result = await f()
    assert isinstance(result, Err)
    assert isinstance(result.err(), ValueError)
    assert str(result.err()) == "oops"

  async def test_catches_arbitrary_exception_subclass(self):
    class MyError(Exception):
      pass

    @catch_async
    async def f():
      raise MyError("custom")

    result = await f()
    assert isinstance(result, Err)
    assert isinstance(result.err(), MyError)

  async def test_does_not_catch_base_exception(self):
    """BaseException (e.g. KeyboardInterrupt) is not a subclass of Exception."""

    @catch_async
    async def f():
      raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
      _ = await f()

  async def test_ok_q_returns_inner_value_and_continues(self):
    @catch_async
    async def f() -> Ok[int] | Err[str]:
      v = Ok(10).q()
      return Ok(v + 1)

    assert await f() == Ok(Ok(11))

  async def test_err_q_raises_early_return_which_is_caught(self):
    """Err.q() raises EarlyReturn, which is an Exception and therefore
    caught by catch_async, yielding Err(EarlyReturn(...))."""

    @catch_async
    async def f():
      Err("fail").q()

    result = await f()
    assert isinstance(result, Err)
    err_value = result.err()
    assert isinstance(err_value, EarlyReturn)
    assert err_value.args[0] == "fail"

  async def test_err_q_non_exception_value_has_no_cause(self):
    """When the stored error is not a BaseException, __cause__ must be None."""

    @catch_async
    async def f():
      Err("plain string").q()

    result = await f()
    assert isinstance(result, Err)
    early = result.err()
    assert isinstance(early, EarlyReturn)
    assert early.__cause__ is None

  async def test_err_q_exception_value_chained_as_cause(self):
    """When the stored error is a BaseException, EarlyReturn is raised
    `from` it, so __cause__ must be that exception."""
    inner = ValueError("inner exc")

    @catch_async
    async def f():
      Err(inner).q()

    result = await f()
    assert isinstance(result, Err)
    early = result.err()
    assert isinstance(early, EarlyReturn)
    assert early.args[0] is inner
    assert early.__cause__ is inner

  async def test_err_q_base_exception_value_chained_as_cause(self):
    """BaseException subclasses (not just Exception) are also chained."""
    inner = KeyboardInterrupt("kbd")

    @catch_async
    async def f():
      Err(inner).q()

    result = await f()
    assert isinstance(result, Err)
    early = result.err()
    assert isinstance(early, EarlyReturn)
    assert early.__cause__ is inner

  async def test_err_q_stops_execution_immediately(self):
    executed: list[str] = []

    @catch_async
    async def f():
      Err("stop").q()
      executed.append("unreachable")  # pyright: ignore[reportUnreachable]

    _ = await f()
    assert executed == []


class TestCatchAsyncWithExceptionTypes:
  """@catch_async(ExcType, ...) - catches only the specified exception types."""

  async def test_catches_specified_exception(self):
    @catch_async(ValueError)
    async def f():
      raise ValueError("val error")

    result = await f()
    assert isinstance(result, Err)
    assert isinstance(result.err(), ValueError)

  async def test_does_not_catch_unspecified_exception(self):
    @catch_async(ValueError)
    async def f():
      raise TypeError("not covered")

    with pytest.raises(TypeError):
      _ = await f()

  async def test_catches_subclass_of_specified_exception(self):
    class MyValueError(ValueError):
      pass

    @catch_async(ValueError)
    async def f():
      raise MyValueError("subclass")

    result = await f()
    assert isinstance(result, Err)
    assert isinstance(result.err(), MyValueError)

  async def test_catches_multiple_specified_exception_types(self):
    @catch_async(ValueError, TypeError)
    async def f(*, raise_value_error: bool):
      if raise_value_error:
        raise ValueError("v")
      raise TypeError("t")

    r1 = await f(raise_value_error=True)
    r2 = await f(raise_value_error=False)
    assert isinstance(r1, Err)
    assert isinstance(r1.err(), ValueError)
    assert isinstance(r2, Err)
    assert isinstance(r2.err(), TypeError)

  async def test_successful_return_still_wrapped_in_ok(self):
    @catch_async(ValueError)
    async def f() -> int:
      return 99

    assert await f() == Ok(99)

  async def test_empty_call_catches_all_exceptions(self):
    """@catch_async() with no args should behave like @catch_async."""

    @catch_async()
    async def f():
      raise RuntimeError("boom")

    result = await f()
    assert isinstance(result, Err)
    assert isinstance(result.err(), RuntimeError)

  async def test_early_return_not_caught_when_not_in_specified_types(self):
    """EarlyReturn is an Exception. If only ValueError is specified,
    EarlyReturn raised by .q() will not be caught and will propagate."""

    @catch_async(ValueError)
    async def f():
      Err("escape").q()

    with pytest.raises(EarlyReturn):
      _ = await f()

  async def test_early_return_propagates_with_correct_cause(self):
    """Even when EarlyReturn escapes, __cause__ is set correctly."""
    inner = ValueError("chained")

    @catch_async(TypeError)  # won't catch EarlyReturn
    async def f():
      Err(inner).q()

    with pytest.raises(EarlyReturn) as exc_info:
      _ = await f()

    assert exc_info.value.__cause__ is inner

  async def test_early_return_caught_when_exception_specified(self):
    """EarlyReturn subclasses Exception, so catch_async(Exception) catches it."""

    @catch_async(Exception)
    async def f():
      Err("caught").q()

    result = await f()
    assert isinstance(result, Err)
    assert isinstance(result.err(), EarlyReturn)


class TestCatchAsyncMetadataPreservation:
  async def test_preserves_function_name(self):
    @catch_async
    async def my_async_fn():
      return 1

    assert my_async_fn.__name__ == "my_async_fn"

  async def test_preserves_docstring(self):
    @catch_async
    async def f():
      """My docstring."""
      return 1

    assert f.__doc__ == "My docstring."

  async def test_preserves_name_with_exception_types(self):
    @catch_async(ValueError)
    async def named_fn():
      return 1

    assert named_fn.__name__ == "named_fn"

  async def test_preserves_docstring_with_exception_types(self):
    @catch_async(ValueError)
    async def f():
      """Another docstring."""
      return 1

    assert f.__doc__ == "Another docstring."


class TestCatchAsyncArguments:
  async def test_positional_args(self):
    @catch_async
    async def f(x: int, y: int) -> int:
      return x + y

    assert await f(3, 4) == Ok(7)

  async def test_keyword_only_args(self):
    @catch_async
    async def f(*, name: str) -> str:
      return f"hi {name}"

    assert await f(name="bob") == Ok("hi bob")

  async def test_mixed_positional_and_keyword_args(self):
    @catch_async
    async def f(x: int, *, multiplier: int) -> int:
      return x * multiplier

    assert await f(3, multiplier=4) == Ok(12)

  async def test_exception_varies_by_arg(self):
    @catch_async
    async def f(x: int):
      if x < 0:
        raise ValueError(f"negative: {x}")
      return x

    assert await f(5) == Ok(5)
    err = await f(-1)
    assert isinstance(err, Err)
    assert isinstance(err.err(), ValueError)


class TestCatchAsyncWithAwait:
  async def test_awaits_inner_coroutine(self):
    @catch_async
    async def f() -> int:
      await asyncio.sleep(0)
      return 1

    assert await f() == Ok(1)

  async def test_exception_raised_after_await(self):
    @catch_async
    async def f():
      await asyncio.sleep(0)
      raise ValueError("after await")

    result = await f()
    assert isinstance(result, Err)
    assert isinstance(result.err(), ValueError)

  async def test_err_q_after_await(self):
    @catch_async
    async def f():
      await asyncio.sleep(0)
      Err("late fail").q()

    result = await f()
    assert isinstance(result, Err)
    assert isinstance(result.err(), EarlyReturn)
    assert result.err().args[0] == "late fail"

  async def test_err_q_exception_cause_preserved_after_await(self):
    inner = RuntimeError("root cause")

    @catch_async
    async def f():
      await asyncio.sleep(0)
      Err(inner).q()

    result = await f()
    assert isinstance(result, Err)
    early = result.err()
    assert isinstance(early, EarlyReturn)
    assert early.__cause__ is inner
