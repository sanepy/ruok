import pytest

from ruok import RE, RS, Err, Ok, Res, is_err, is_ok


def test_res_ok():
  res: Res[int, str] = Ok(1)
  if is_ok(res):
    assert res.ok() + 1 == 2
  else:
    pytest.fail("Expected Ok")  # pyright: ignore[reportUnreachable]


def test_res_err():
  res: Res[int, str] = Err("fail")
  if is_err(res):
    assert res.err() + "!" == "fail!"
  else:
    pytest.fail("Expected Err")  # pyright: ignore[reportUnreachable]


def test_re_ok():
  res: RE[float] = Ok(3.14)
  if is_ok(res):
    assert res.ok() > 0


def test_re_err():
  exc = ValueError("boom")
  res: RE[float] = Err(exc)
  if is_err(res):
    assert isinstance(res.err(), Exception)


def test_r_ok():
  res: RS[float] = Ok(6.0)
  b = 6.0
  if is_ok(res):
    assert res.ok() + b == 12.0
  else:
    pytest.fail("Expected Ok")  # pyright: ignore[reportUnreachable]


def test_r_err():
  res: RS[float] = Err("not a number")
  if is_err(res):
    assert "asdf" + res.err() == "asdfnot a number"
  else:
    pytest.fail("Expected Err")  # pyright: ignore[reportUnreachable]


@pytest.mark.parametrize("value", [1, "x", None, 3.14, []])
def test_res_roundtrip_ok(value: object):
  res: Res[object, str] = Ok(value)
  assert is_ok(res)
  assert res.ok() is value


@pytest.mark.parametrize("value", ["err", "timeout", ""])
def test_r_roundtrip_err(value: str):
  res: RS[int] = Err(value)
  assert is_err(res)
  assert res.err() == value
