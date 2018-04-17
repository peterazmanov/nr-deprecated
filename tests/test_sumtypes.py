
from nose.tools import *
from nr import sumtypes


def test_sumtypes():

  class Result(sumtypes.Type):
    __addins__ = [sumtypes.IsConstructorMethods]  # Default addin
    Loading = sumtypes.Constructor('progress')
    Error = sumtypes.Constructor('message')
    Ok = sumtypes.Constructor('filename', 'load')

    @sumtypes.MemberOf([Loading])
    def alert(self):
      return 'Progress: ' + str(self.progress)

    static_error_member = sumtypes.MemberOf([Error], 'This is a member on Error!')

  assert not hasattr(Result, 'alert')
  assert not hasattr(Result, 'static_error_member')

  x = Result.Loading(0.5)
  assert isinstance(x, Result)
  assert x.is_loading()
  assert not x.is_error()
  assert not x.is_ok()
  assert hasattr(x, 'alert')
  assert not hasattr(x, 'static_error_member')
  assert_equals(x.alert(), 'Progress: 0.5')
  assert_equals(x.progress, 0.5)
