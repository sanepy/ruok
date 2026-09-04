import linecache
import os
import re
import shutil
import site
import sys
import sysconfig
import textwrap
import traceback
from collections.abc import Sequence
from pathlib import Path
from types import TracebackType
from typing import TextIO, cast

_ANSI_RE = re.compile(r"\033\[[^m]*m")
_TOKEN_RE = re.compile(f"{_ANSI_RE.pattern}|.")

_MIN_CONTENT_WIDTH = 20

_RESET = "\033[0m"
_BOLD = "\033[1m"
_WHITE = "\033[38;2;220;220;220m"
_DEEP_CRIMSON = "\033[38;2;175;0;95m"  # af005f
_PERIWINKLE = "\033[38;2;95;95;255m"  # 5f5fff
_DUSK_ROSE = "\033[38;2;195;135;120m"  # C38778


def error_displayer(
  exc: BaseException,
  hops: Sequence[TracebackType] = (),
  *,
  show_propagation: bool = False,
  color: bool | None = None,
  file: TextIO | None = None,
) -> None:
  """Render an exception with ANSI styling to a stream."""
  stream = file or sys.stderr

  def _supports_color(
    stream: TextIO,
    *,
    override: bool | None = None,
  ) -> bool:
    if override is not None:
      return override
    if os.environ.get("NO_COLOR"):
      return False
    if os.environ.get("FORCE_COLOR"):
      return True
    return hasattr(stream, "isatty") and stream.isatty()

  color = _supports_color(stream, override=color)

  border_and_padding = 4
  wrap_width = max(
    shutil.get_terminal_size().columns - border_and_padding, _MIN_CONTENT_WIDTH
  )

  noise_prefixes: tuple[Path, ...] = tuple(
    Path(p).resolve()
    for p in (
      sysconfig.get_paths()["stdlib"],
      *(site.getsitepackages() if hasattr(site, "getsitepackages") else []),
      *([site.getusersitepackages()] if hasattr(site, "getusersitepackages") else []),
    )
  )

  def _visible_len(s: str) -> int:
    return len(_ANSI_RE.sub("", s))

  def _wrap(text: str, *, width: int) -> list[str]:
    out: list[str] = []
    for line in text.splitlines() or [""]:
      out.extend(textwrap.wrap(line, width=width) or [""])
    return out

  def _style(text: str, *codes: str, color: bool) -> str:
    if not color or not codes:
      return text
    return f"{''.join(codes)}{text}{_RESET}"

  def _best_frame(
    tb: TracebackType | None,
  ) -> traceback.FrameSummary | None:
    if tb is None:
      return None

    def _is_noise_frame(filename: str) -> bool:
      if not filename or filename.startswith("<"):
        return True
      resolved = Path(filename).resolve()
      return any(resolved == p or resolved.is_relative_to(p) for p in noise_prefixes)

    frames = traceback.extract_tb(tb)
    user_frames: list[traceback.FrameSummary] = [
      f for f in frames if not _is_noise_frame(f.filename)
    ]
    candidates = user_frames or frames
    return candidates[-1] if candidates else None

  def _render_error(
    exc: BaseException,
    *,
    color: bool,
    wrap_width: int,
  ) -> list[str]:
    def _cause_chain(exc: BaseException) -> list[BaseException]:
      seen: set[int] = set()
      chain: list[BaseException] = []
      cur: BaseException | None = exc
      while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        chain.append(cur)
        nxt: BaseException | None = cur.__cause__
        if nxt is None and not cur.__suppress_context__:
          nxt = cur.__context__
        cur = nxt
      return chain

    chain: list[BaseException] = _cause_chain(exc)
    cwd: Path = Path.cwd()
    lines: list[str] = []

    def _render_header(
      error: BaseException,
    ) -> list[str]:
      err_type: str = type(error).__qualname__
      err_msg: str = str(error)
      tag = f"[{err_type}]"
      text = f"{err_msg.strip()} {tag}" if err_msg else tag
      wrapped = _wrap(text, width=wrap_width)

      styled = [_style(t, _BOLD, _DEEP_CRIMSON, color=color) for t in wrapped[:-1]]
      last_msg = wrapped[-1][: -len(tag)]
      styled.append(
        _style(last_msg, _BOLD, _DEEP_CRIMSON, color=color)
        + _style(tag, _BOLD, _WHITE, color=color)
      )
      return styled

    for idx, error in enumerate(chain):
      lines.extend(_render_header(error))

      frame = _best_frame(error.__traceback__)
      if not (frame and frame.filename and frame.lineno):
        continue

      try:
        path = Path(frame.filename).relative_to(cwd)
      except ValueError:
        path = Path(frame.filename)

      loc = "  "
      if frame.name not in {"<module>", "<lambda>", "<genexpr>"}:
        loc += _style(f"{frame.name}()", _BOLD, _DUSK_ROSE, color=color) + " "
      loc += _style(path.name, _BOLD, _DUSK_ROSE, color=color)
      loc += _style(f" {frame.lineno}", _BOLD, _DUSK_ROSE, color=color)
      parent = str(path.parent)
      if parent and parent != ".":
        loc += " " + _style(f"{parent}/", _BOLD, _DUSK_ROSE, color=color)
      lines.append(loc)

      def _source_lines(
        filename: str,
        lineno: int,
        *,
        radius: int = 2,
      ) -> list[tuple[int, str, bool]]:
        out: list[tuple[int, str, bool]] = []
        trailing_blanks = 0
        for n in range(lineno - radius, lineno + radius + 1):
          line = linecache.getline(filename, n)
          if not line:
            continue
          text = line.rstrip()
          if not text.strip():
            if not out:
              continue
            trailing_blanks += 1
          else:
            trailing_blanks = 0
          out.append((n, text, n == lineno))

        if trailing_blanks:
          out = out[:-trailing_blanks]

        if not out:
          return []

        dedented = textwrap.dedent("\n".join(t for _, t, _ in out)).split("\n")
        return [
          (n, d, is_target) for (n, _, is_target), d in zip(out, dedented, strict=True)
        ]

      src = _source_lines(frame.filename, frame.lineno)
      if not src:
        continue

      w = len(str(src[-1][0]))
      pad = " " * (w + 3)
      lines.append(f"{pad}{_style('╭─', _PERIWINKLE, color=color)}")

      for n, text, hi in src:
        num = str(n).rjust(w)
        bar = _style("│", _PERIWINKLE, color=color)
        if hi:
          marker = _style(">", _BOLD, _PERIWINKLE, color=color)
          styled_num = _style(num, _WHITE, color=color)
          styled_text = _style(text, _BOLD, _DEEP_CRIMSON, color=color)
          lines.append(f"{marker} {styled_num} {bar} {styled_text}")
        else:
          styled_num = _style(num, _WHITE, color=color)
          styled_text = _style(text, _BOLD, _WHITE, color=color)
          lines.append(f"  {styled_num} {bar} {styled_text}")

      if idx < len(chain) - 1:
        tail = _style("╰─", _PERIWINKLE, color=color)
        caused = _style("caused by:", _BOLD, _WHITE, color=color)
        lines.append(f"{pad}{tail} {caused}")
      else:
        lines.append(f"{pad}{_style('╰─', _PERIWINKLE, color=color)}")

    return lines

  def _is_message(exc: BaseException) -> bool:
    """An EarlyReturn with a non-exception payload and nothing chained
    underneath is a message to the user, not an error to render."""
    # Imported lazily because ruok.ruok imports this module at its top, and
    # creating a new file is not warranted
    from ruok.ruok import (  # noqa: PLC0415
      EarlyReturn,
    )

    if not isinstance(exc, EarlyReturn) or not exc.args:
      return False
    if isinstance(exc.args[0], BaseException):
      return False
    if exc.__cause__ is not None:
      return False
    return exc.__suppress_context__ or exc.__context__ is None

  if _is_message(exc):
    content = _wrap(str(cast("object", exc.args[0])), width=wrap_width)
  else:
    content = _render_error(exc, color=color, wrap_width=wrap_width)

    if show_propagation and hops:

      def _render_propagation(
        hops: Sequence[TracebackType],
        *,
        color: bool,
      ) -> list[str]:
        """Render the EarlyReturn propagation footer."""
        hop_frames = [_best_frame(tb) for tb in hops]
        clean = [f for f in hop_frames if f is not None]
        if not clean:
          return []

        cwd = Path.cwd()
        lines: list[str] = [
          "",
          _style(
            f"Propagated via EarlyReturn \u00d7 {len(clean)}:",
            _BOLD,
            _WHITE,
            color=color,
          ),
        ]

        for hop in reversed(clean):
          try:
            path = Path(hop.filename).relative_to(cwd)
          except ValueError:
            path = Path(hop.filename)

          entry = "  " + _style("\u2192", _WHITE, color=color) + " "
          if hop.name not in {"<module>", "<lambda>", "<genexpr>"}:
            entry += _style(f"{hop.name}()", _BOLD, _DUSK_ROSE, color=color) + " "
          entry += _style(path.name, _BOLD, _DUSK_ROSE, color=color)
          entry += _style(f" {hop.lineno}", _BOLD, _DUSK_ROSE, color=color)
          parent = str(path.parent)
          if parent and parent != ".":
            entry += " " + _style(f"{parent}/", _BOLD, _DUSK_ROSE, color=color)
          lines.append(entry)

        return lines

      content.extend(_render_propagation(hops, color=color))

  if content:

    def _ensure_width(s: str, *, width: int) -> str:
      if _visible_len(s) <= width:
        return s
      out: list[str] = []
      visible = 0
      for m in _TOKEN_RE.finditer(s):
        tok = m.group()
        if tok.startswith("\033"):
          out.append(tok)
          continue
        if visible >= width - 1:
          break
        out.append(tok)
        visible += 1
      text = "".join(out) + "\u2026"
      return f"{text}{_RESET}" if "\033" in text else text

    def _draw_panel(
      content: list[str],
      *,
      color: bool,
      stream: TextIO,
      wrap_width: int,
    ) -> None:
      lines = [_ensure_width(line, width=wrap_width) for line in content]
      max_width = max(
        (_visible_len(line) for line in lines),
        default=0,
      )
      border = "\u2500" * (max_width + 2)

      top = _style(f"\u256d{border}\u256e", _PERIWINKLE, color=color)
      bot = _style(f"\u2570{border}\u256f", _PERIWINKLE, color=color)
      left = _style("\u2502", _PERIWINKLE, color=color)
      right = _style("\u2502", _PERIWINKLE, color=color)

      _ = stream.write(f"\n{top}\n")
      for line in lines:
        padding = " " * (max_width - _visible_len(line))
        _ = stream.write(f"{left} {line}{padding} {right}\n")
      _ = stream.write(f"{bot}\n")

    _draw_panel(content, color=color, stream=stream, wrap_width=wrap_width)
