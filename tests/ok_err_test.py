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

  s = {Ok(1), Ok(2), Ok(1)}
  assert len(s) == 2

  d = {Ok("k"): "v"}
  assert d[Ok("k")] == "v"

  assert hash(Ok(1)) == hash(Ok(1))

  assert hash(Ok(1)) != hash(Err(1))

  with pytest.raises(TypeError):
    _ = hash(Ok([1, 2, 3]))

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

  s = {Err(1), Err(2), Err(1)}
  assert len(s) == 2

  d = {Err("k"): "v"}
  assert d[Err("k")] == "v"

  assert hash(Err(1)) == hash(Err(1))

  assert hash(Err(1)) != hash(Ok(1))

  with pytest.raises(TypeError):
    _ = hash(Err([1, 2, 3]))

  with pytest.raises(EarlyReturn):
    _ = Err("result").q()

  assert not hasattr(Err(obj), "ok")
