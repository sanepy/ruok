import pytest

from ruok import Err, Ok, is_err, is_ok


@pytest.mark.parametrize("value", [0, "", None, False, [], Ok(1), Err("x")])
def test_is_ok_true_for_ok(value: object):
  assert is_ok(Ok(value)) is True


@pytest.mark.parametrize("value", [0, "", None, False, [], Ok(1), Err("x")])
def test_is_ok_false_for_err(value: object):
  assert is_ok(Err(value)) is False


@pytest.mark.parametrize("value", [0, "", None, False, [], Ok(1), Err("x")])
def test_is_err_true_for_err(value: object):
  assert is_err(Err(value)) is True


@pytest.mark.parametrize("value", [0, "", None, False, [], Ok(1), Err("x")])
def test_is_err_false_for_ok(value: object):
  assert is_err(Ok(value)) is False


def test_is_ok_narrows_in_branch():
  result: Ok[int] | Err[str] = Ok(5)
  if is_ok(result):
    assert result.ok() == 5


def test_is_ok_narrows_in_branch_else():
  result: Ok[int] | Err[str] = Ok(5)
  if not is_ok(result):
    pytest.fail("the code should not reach here")  # pyright: ignore[reportUnreachable]
  else:
    assert result.ok() == 5


def test_is_err_narrows_in_branch():
  result: Ok[int] | Err[str] = Err("bad")
  if is_err(result):
    assert result.err() == "bad"


def test_is_err_narrows_in_branch_else():
  result: Ok[int] | Err[str] = Ok(1)
  if is_err(result):
    pytest.fail("the code should not reach here")  # pyright: ignore[reportUnreachable]
  else:
    assert result.ok() == 1
