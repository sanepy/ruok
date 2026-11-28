"""Manual visual checks for the error renderer, not collected by pytest.

Usage:
  python -m tests.visual              list all scenarios
  python -m tests.visual --all        run every non-interactive scenario
  python -m tests.visual NAME ...     run scenarios by full name, e.g. messages.long
  python -m tests.visual MODULE ...   run all scenarios in a module, e.g. messages
"""

import sys
from collections.abc import Callable

from tests.visual import errors, fallback, interrupt, messages

SCENARIOS: dict[str, Callable[[], None]] = {
  "messages.short": messages.scenario_short,
  "messages.long": messages.scenario_long,
  "messages.multiline": messages.scenario_multiline,
  "messages.nested_unstripped": messages.scenario_nested_unstripped,
  "errors.simple": errors.scenario_simple,
  "errors.long_message": errors.scenario_long_message,
  "errors.no_border": errors.scenario_no_border,
  "errors.long_source_line": errors.scenario_long_source_line,
  "errors.chain": errors.scenario_chain,
  "errors.nested_error": errors.scenario_nested_error,
  "fallback.handler_fails": fallback.scenario_handler_fails,
  "fallback.handler_fails_with_cause": fallback.scenario_handler_fails_with_cause,
  "fallback.both_fail": fallback.scenario_both_fail,
  "interrupt.ctrl_c": interrupt.scenario_ctrl_c,
  "interrupt.via_q": interrupt.scenario_via_q,
}

INTERACTIVE = {"interrupt.ctrl_c"}


def _out(text: str = "") -> None:
  _ = sys.stdout.write(f"{text}\n")


def _run(name: str, scenario: Callable[[], None]) -> None:
  _out(f"--- {name} ---")
  try:
    scenario()
  except SystemExit as exc:
    _out(f"exit code: {exc.code}")
  _out()


def main() -> None:
  args = sys.argv[1:]

  if not args:
    _out("Available scenarios:")
    _out()
    for name in SCENARIOS:
      _out(f"  {name}")
    _out()
    _out("Run: python -m tests.visual --all | MODULE | NAME ...")
    return

  if args == ["--all"]:
    for name, scenario in SCENARIOS.items():
      if name not in INTERACTIVE:
        _run(name, scenario)
    _out(
      f"(interactive ones need to be run individually: {', '.join(sorted(INTERACTIVE))})"
    )
    return

  for name in args:
    matches = {
      n: s for n, s in SCENARIOS.items() if n == name or n.startswith(f"{name}.")
    }
    if not matches:
      _out(f"Unknown scenario: {name}")
      raise SystemExit(2)
    for match_name, scenario in matches.items():
      _run(match_name, scenario)


if __name__ == "__main__":
  main()
