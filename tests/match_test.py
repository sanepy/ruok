from ruok import Err, Ok, Res


def test_pattern_matching_on_ok_type() -> None:
  res: Res[str, int] = Ok("yay")
  match res:
    case Ok(value):
      reached = True

  assert value == "yay"
  assert reached


def test_pattern_matching_on_err_type() -> None:
  res: Res[int, str] = Err("nay")
  match res:
    case Err(value):
      reached = True

  assert value == "nay"
  assert reached
