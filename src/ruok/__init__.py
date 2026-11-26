from ruok.ruok import (
  RE,
  RS,
  EarlyReturn,
  Err,
  Ok,
  Res,
  catch,
  display_error,
  is_err,
  is_ok,
)

__all__ = [
  "RE",
  "RS",
  "EarlyReturn",
  "Err",
  "Ok",
  "Res",
  "catch",
  "display_error",
  "is_err",
  "is_ok",
]

# Present public names as defined in the top-level package ("ruok.Err", not
# "ruok.ruok.Err") in error messages, class reprs, docs, and pickle paths.
# A similar approach is used, for example, in the Python library Trio.
for _obj in (Ok, Err, EarlyReturn, catch, display_error, is_err, is_ok):
  _obj.__module__ = "ruok"

del _obj
