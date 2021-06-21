import typing as t


CatchExceptionCallable = t.Callable[[Exception, "ErrorResponse"], t.NoReturn]
