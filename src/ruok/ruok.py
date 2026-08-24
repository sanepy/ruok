import inspect
import sys
from collections.abc import Awaitable, Callable
from functools import wraps
from types import TracebackType
from typing import (
  NoReturn,
  Protocol,
  TypeIs,
  cast,
  final,
  overload,
  override,
)

from ruok._error_displayer import error_displayer


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


class _CatchProtocol(Protocol):
  @overload
  def __call__[**P, T](  # pyright: ignore[reportOverlappingOverload]
    self,
    f: Callable[P, Awaitable[T]],
  ) -> Callable[P, Awaitable[RE[T]]]: ...

  @overload
  def __call__[**P, T](
    self,
    f: Callable[P, T],
  ) -> Callable[P, RE[T]]: ...

  def __call__(
    self,
    f: Callable[..., object],
  ) -> Callable[..., object]: ...


@overload
def catch[E: Exception](
  *exceptions: type[E],
) -> _CatchProtocol: ...


@overload
def catch[**P, T](  # pyright: ignore[reportOverlappingOverload]
  f: Callable[P, Awaitable[T]],
  /,
) -> Callable[P, Awaitable[RE[T]]]: ...


@overload
def catch[**P, T](f: Callable[P, T], /) -> Callable[P, RE[T]]: ...


def catch(*exceptions_or_func: object) -> object:
  def _make_decorator(
    exceptions: tuple[type[Exception], ...],
  ) -> Callable[[Callable[..., object]], Callable[..., object]]:
    def decorator(f: Callable[..., object]) -> Callable[..., object]:
      if inspect.iscoroutinefunction(f):

        @wraps(f)
        async def async_wrapper(*args: object, **kwargs: object) -> RE[object]:
          try:
            return Ok(await cast("Awaitable[object]", f(*args, **kwargs)))
          except exceptions as exc:
            return Err(exc)

        return async_wrapper

      @wraps(f)
      def sync_wrapper(*args: object, **kwargs: object) -> RE[object]:
        try:
          return Ok(f(*args, **kwargs))
        except exceptions as exc:
          return Err(exc)

      return sync_wrapper

    return decorator

  match exceptions_or_func:
    case (f,) if callable(f) and not (
      isinstance(f, type) and issubclass(f, BaseException)
    ):
      # Cast needed because non-exception classes are typed as type[Unknown]
      return _make_decorator((Exception,))(cast("Callable[..., object]", f))
    case _:
      resolved = cast("tuple[type[Exception], ...]", exceptions_or_func) or (Exception,)
      # Cast needed because iscoroutinefunction dispatch is runtime
      return cast("_CatchProtocol", _make_decorator(resolved))


class _DisplayErrorProtocol(Protocol):
  @overload
  def __call__[**P, T](
    self,
    f: Callable[P, Awaitable[T]],
  ) -> Callable[P, Awaitable[T]]: ...

  @overload
  def __call__[**P, T](
    self,
    f: Callable[P, T],
  ) -> Callable[P, T]: ...

  def __call__(
    self,
    f: Callable[..., object],
  ) -> Callable[..., object]: ...


@overload
def display_error[**P, T](
  f: Callable[P, Awaitable[T]],
  /,
) -> Callable[P, Awaitable[T]]: ...


@overload
def display_error[**P, T](
  f: Callable[P, T],
  /,
) -> Callable[P, T]: ...


@overload
def display_error(
  *,
  handler: Callable[[BaseException], None] | None = None,
  displayer: Callable[[BaseException], None] | None = None,
  strip_early_returns: bool = True,
  show_propagation: bool = False,
  raw_raise: bool = False,
  color: bool | None = None,
) -> _DisplayErrorProtocol: ...


def display_error(
  f: Callable[..., object] | None = None,
  /,
  *,
  handler: Callable[[BaseException], None] | None = None,
  displayer: Callable[[BaseException], None] | None = None,
  strip_early_returns: bool = True,
  show_propagation: bool = False,
  raw_raise: bool = False,
  color: bool | None = None,
) -> object:
  """Decorator that renders exceptions.

  Intended to wrap the program's top-level entry point (e.g., `main()`)

  Args:
    handler: Callback for side effects (e.g., logging or telemetry).
    displayer: Renderer to override the built-in ANSI terminal output.
    strip_early_returns: Traverses the exception chain and
      strips `EarlyReturn` exceptions.
    show_propagation: Renders an additional footer trace detailing
      each frame where an `EarlyReturn` was propagated.
    raw_raise: Disables exception interception and lets errors propagate normally.
    color: Force-enables (`True`) or disables (`False`) ANSI color output. When
      `None`, auto-detects support via TTY checks and `NO_COLOR`/`FORCE_COLOR`
      environment variables.

  Returns:
    A decorator capable of wrapping both sync and async functions.
  """

  def _handle_exception(exc: BaseException) -> None:
    if strip_early_returns:

      def _strip_early_returns(
        exc: BaseException,
      ) -> tuple[BaseException, list[TracebackType]]:
        original: BaseException = exc
        seen: set[int] = set()
        hops: list[TracebackType] = []

        while isinstance(exc, EarlyReturn) and id(exc) not in seen:
          seen.add(id(exc))
          if exc.__traceback__ is not None:
            hops.append(exc.__traceback__)
          if exc.__cause__ is not None:
            exc = exc.__cause__
          elif exc.args and isinstance(exc.args[0], BaseException):
            exc = exc.args[0]
          else:
            return original, []

        return exc, hops

      cleaned, hops = _strip_early_returns(exc)
    else:
      cleaned, hops = exc, ()

    if handler is not None:
      try:
        handler(cleaned)
      except Exception as handler_exc:
        handler_exc.__suppress_context__ = True
        _ = sys.stderr.write("Custom handler raised an exception:")
        error_displayer(handler_exc, color=color)

    if displayer is not None:
      try:
        displayer(cleaned)
      except Exception as displayer_exc:
        displayer_exc.__suppress_context__ = True
        _ = sys.stderr.write("Custom displayer raised an exception:")
        error_displayer(displayer_exc, color=color)
        _ = sys.stderr.write("Original exception:")
        error_displayer(
          cleaned,
          hops,
          color=color,
          show_propagation=show_propagation,
        )
    else:
      error_displayer(
        cleaned,
        hops,
        color=color,
        show_propagation=show_propagation,
      )

  def decorator(
    f: Callable[..., object],
  ) -> Callable[..., object]:
    if raw_raise:
      return f

    if inspect.iscoroutinefunction(f):

      @wraps(f)
      async def async_wrapper(*args: object, **kwargs: object) -> object:
        try:
          return cast("object", await f(*args, **kwargs))
        except (Exception, KeyboardInterrupt) as exc:
          _handle_exception(exc)
          sys.exit(1)

      return async_wrapper

    @wraps(f)
    def sync_wrapper(*args: object, **kwargs: object) -> object:
      try:
        return f(*args, **kwargs)
      except (Exception, KeyboardInterrupt) as exc:
        _handle_exception(exc)
        sys.exit(1)

    return sync_wrapper

  if f is not None:
    return decorator(f)

  return cast("_DisplayErrorProtocol", decorator)
