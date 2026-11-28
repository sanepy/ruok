"""KeyboardInterrupt scenarios. Run ctrl_c individually, it needs a real Ctrl-C."""

from time import sleep

from ruok import Err, display_error


@display_error
def scenario_ctrl_c() -> None:
  sleep(10)


@display_error
def scenario_via_q() -> None:
  Err(KeyboardInterrupt("kbd")).q()
