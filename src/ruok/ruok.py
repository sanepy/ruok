from collections.abc import Awaitable, Callable
from functools import wraps
from typing import (
  NoReturn,
  TypeIs,
  cast,
  final,
  overload,
  override,
)


@final
class Ok[T]:
  """A value that indicates success, storing arbitrary data for the return value."""

  __slots__ = ("_value",)
  __match_args__ = ("_value",)

  def __init__(self, value: T) -> None:
    self._value = value

  @override
  def __repr__(self) -> str:
    return f"Ok({self._value!r})"

  @override
  def __eq__(self, other: object) -> bool:
    return isinstance(other, Ok) and self._value == other._value

  @override
  def __hash__(self) -> int:
    return hash((True, self._value))

  def ok(self) -> T:
    return self._value

  def q(self) -> T:
    return self._value


@final
class Err[E]:
  """A value that indicates failure, storing arbitrary data for the error."""

  __slots__ = ("_value",)
  __match_args__ = ("_value",)

  def __init__(self, value: E) -> None:
    self._value = value

  @override
  def __repr__(self) -> str:
    return f"Err({self._value!r})"

  @override
  def __eq__(self, other: object) -> bool:
    return isinstance(other, Err) and self._value == other._value

  @override
  def __hash__(self) -> int:
    return hash((False, self._value))

  def err(self) -> E:
    return self._value

  def q(self) -> NoReturn:
    err = self.err()
    raise EarlyReturn(err) from (err if isinstance(err, BaseException) else None)


type Res[T, E] = Ok[T] | Err[E]
type RE[T] = Ok[T] | Err[Exception]
type RS[T] = Ok[T] | Err[str]


def is_ok[T, E](result: Res[T, E]) -> TypeIs[Ok[T]]:
  return isinstance(result, Ok)


def is_err[T, E](result: Res[T, E]) -> TypeIs[Err[E]]:
  return isinstance(result, Err)


class EarlyReturn(Exception):
  pass


@overload
def catch[E: Exception, **P, T](
  *exceptions: type[E],
) -> Callable[[Callable[P, T]], Callable[P, RE[T]]]: ...


@overload
def catch[**P, T](f: Callable[P, T], /) -> Callable[P, RE[T]]: ...


def catch(*exceptions_or_func: object) -> object:
  def _make_decorator(
    exceptions: tuple[type[Exception], ...],
  ) -> Callable[[Callable[..., object]], Callable[..., RE[object]]]:
    def decorator(f: Callable[..., object]) -> Callable[..., RE[object]]:
      @wraps(f)
      def wrapper(*args: object, **kwargs: object) -> RE[object]:
        try:
          return Ok(f(*args, **kwargs))
        except exceptions as exc:
          return Err(exc)

      return wrapper

    return decorator

  match exceptions_or_func:
    case (f,) if callable(f) and not isinstance(f, type):
      return _make_decorator((Exception,))(f)
    case _:
      resolved = cast("tuple[type[Exception], ...]", exceptions_or_func) or (Exception,)
      return _make_decorator(resolved)


@overload
def catch_async[E: Exception, **P, T](
  *exceptions: type[E],
) -> Callable[
  [Callable[P, Awaitable[T]]],
  Callable[P, Awaitable[RE[T]]],
]: ...


@overload
def catch_async[**P, T](
  f: Callable[P, Awaitable[T]],
  /,
) -> Callable[P, Awaitable[RE[T]]]: ...


def catch_async(*exceptions_or_func: object) -> object:
  def _make_decorator(
    exceptions: tuple[type[Exception], ...],
  ) -> Callable[
    [Callable[..., Awaitable[object]]],
    Callable[..., Awaitable[RE[object]]],
  ]:
    def decorator(
      f: Callable[..., Awaitable[object]],
    ) -> Callable[..., Awaitable[RE[object]]]:
      @wraps(f)
      async def wrapper(*args: object, **kwargs: object) -> RE[object]:
        try:
          return Ok(await f(*args, **kwargs))
        except exceptions as exc:
          return Err(exc)

      return wrapper

    return decorator

  match exceptions_or_func:
    case (f,) if callable(f) and not isinstance(f, type):
      return _make_decorator((Exception,))(cast("Callable[..., Awaitable[object]]", f))
    case _:
      resolved = cast("tuple[type[Exception], ...]", exceptions_or_func) or (Exception,)
      return _make_decorator(resolved)


def display_error[**P, T](
  handler: Callable[[BaseException], None] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T | None]]:
  def decorator(f: Callable[P, T]) -> Callable[P, T | None]:
    @wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | None:
      if handler is None:
        raise NotImplementedError("The built-in displayer is not implemented yet")
      try:
        return f(*args, **kwargs)
      except Exception as exc:
        handler(exc)
        return None

    return wrapper

  return decorator


def display_error_async[**P, T](
  handler: Callable[[BaseException], None] | None = None,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T | None]]]:
  def decorator(
    f: Callable[P, Awaitable[T]],
  ) -> Callable[P, Awaitable[T | None]]:
    @wraps(f)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | None:
      if handler is None:
        raise NotImplementedError("The built-in displayer is not implemented yet")
      try:
        return await f(*args, **kwargs)
      except Exception as exc:
        handler(exc)
        return None

    return wrapper

  return decorator
