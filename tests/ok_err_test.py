import pytest

from ruok import EarlyReturn, Err, Ok


def test_ok() -> None:
  assert Ok(100).ok() == 100

  assert Ok(None).ok() is None

  obj = object()
  assert Ok(obj).ok() is obj

  inner = Ok(1)
  assert Ok(inner).ok() is inner

  assert Ok(1) == Ok(1)

  assert Ok(1) != Ok(2)

  assert Ok(1) != Err(1)

  assert Ok(1) != 1

  assert Ok(None) is not None

  assert Ok("result").q() == "result"

  _ = Ok(0).q()

  assert not hasattr(Ok(obj), "err")


def test_err():
  assert Err(100).err() == 100

  assert Err(None).err() is None

  obj = object()
  assert Err(obj).err() is obj

  inner = Err(1)
  assert Err(inner).err() is inner

  assert Err(1) == Err(1)

  assert Err(1) != Err(2)

  assert Err(1) != Ok(1)

  assert Err(1) != 1

  assert Err(None) is not None

  with pytest.raises(EarlyReturn):
    _ = Err("result").q()

  assert not hasattr(Err(obj), "ok")
