"""
Async Utilities.
"""

from __future__ import annotations
from contextlib import suppress
import inspect
import asyncio
from asyncio import Future, Task
from threading import local
from concurrent.futures import Executor, Future as SyncFuture
from contextvars import copy_context
from functools import wraps, partial
import threading
from typing import (Literal, Sequence, TypeVar, Any,
                    Callable, cast, overload, Awaitable,
                    Generator, AsyncGenerator, ParamSpec)
import nest_asyncio

K = TypeVar("K")
V = TypeVar("V")
D = TypeVar("D")
T = TypeVar("T")
A = TypeVar("A", bound=Awaitable)
ARGS = ParamSpec("ARGS")
_LOCAL = local()

__all__ = ("sync_await", "ensure_async", "to_async", "to_async_gen",
           "get_create_loop", "async_run", "select", "wait_until")


def sync_await(fut: Awaitable[V],
               loop: asyncio.AbstractEventLoop = None, timeout: float = None) -> V:
    """
    Get future in a synchronous context.

    This function is thread-safe. However, its behavior is varies.
    If the thread of the loop is the same as the current thread,
    the function will start the loop and wait for the future to complete.

    If the thread of the loop is different from the current thread,
    the function will NOT start the loop.
    **Be careful!** If the loop is not running, the function will block.
    Or if join this thread from which the loop is running, the function will block.

    * `fut` - the awaitable to wait for
    * `loop` - the event loop to use
    * `timeout` - the timeout in seconds if loop is in another thread
    """

    loop = loop or get_create_loop()
    if loop._thread_id in (None, threading.get_ident()):  # type: ignore
        nest_asyncio.apply(loop)
        return loop.run_until_complete(fut)

    # If loop is running in another thread
    syncfuture = SyncFuture[V]()

    def callsoon():
        """workaround for thread safety"""
        def callback(future: Future):
            try:
                syncfuture.set_result(future.result())
            except asyncio.CancelledError:
                syncfuture.cancel()
            except BaseException as e:
                syncfuture.set_exception(e)

        async def wrap():
            return await fut
        try:
            loop.create_task(wrap()).add_done_callback(callback)  # type: ignore
        except BaseException as e:  # pragma: no cover # Hard to test
            syncfuture.set_exception(e)

    loop.call_soon_threadsafe(callsoon)
    return syncfuture.result(timeout=timeout)


@overload
def ensure_async(item: Callable[ARGS, A], loop: asyncio.AbstractEventLoop = None,
                 executor: Executor = None) -> Callable[ARGS, A]: ...


@overload
def ensure_async(item: Callable[ARGS, T], loop: asyncio.AbstractEventLoop = None,
                 executor: Executor = None) -> Callable[ARGS, Awaitable[T]]: ...


@overload
def ensure_async(item: Generator[K, None, V], loop: asyncio.AbstractEventLoop = None,
                 executor: Executor = None) -> AsyncGenerator[K, V]: ...


def ensure_async(item, loop=None, executor=None):
    """
    Convert a sync function or generator to async. Returns the
    original item if it is already a coroutine or an async generator.
    """
    if asyncio.iscoroutinefunction(item) or inspect.isasyncgen(item):
        return item
    if inspect.isgenerator(item):
        return to_async_gen(item, loop, executor)
    if callable(item):
        return to_async(item, loop, executor)
    raise TypeError(f"Expected a callable or generator, got {type(item)}")


def to_async(func: Callable[ARGS, T], loop: asyncio.AbstractEventLoop = None,
             executor: Executor = None) -> Callable[ARGS, Awaitable[T]]:
    """Ensure that the sync function is run within the event loop.
    If the *func* is not a coroutine it will be wrapped such that
    it runs in the default executor (use loop.set_default_executor
    to change). This ensures that synchronous functions do not
    block the event loop.
    """

    @wraps(func)
    async def _wrapper(*args: Any, **kwargs: Any) -> Any:
        nonlocal loop
        _loop = loop or asyncio.get_running_loop()
        return await _loop.run_in_executor(
            executor, copy_context().run, partial(func, *args, **kwargs)
        )

    return _wrapper


def to_async_gen(gen: Generator[T, D, None],
                 loop: asyncio.AbstractEventLoop = None,
                 executor: Executor = None) -> AsyncGenerator[T, D]:
    async def _gen_wrapper():
        # Wrap the generator such that each iteration runs
        # in the executor.
        nonlocal loop

        _loop = loop or asyncio.get_running_loop()

        def _run(f, v):
            """Wraps .send, .throw, .close"""
            ctx = copy_context()

            def _inner():
                try:
                    return ctx.run(f, v)
                except StopIteration as e:
                    # StopIteration has special meaning
                    raise StopAsyncIteration from e

            return _loop.run_in_executor(executor, _inner)

        try:
            ret = await _run(next, gen)

            while True:
                try:
                    v = yield ret
                except Exception as e:  # skipcq: PYL-W0703
                    ret = await _run(gen.throw, e)
                except GeneratorExit:
                    # Unable to wrap close to async
                    gen.close()
                    raise
                else:
                    ret = await _run(gen.send, v)

        except StopAsyncIteration:
            return

    return _gen_wrapper()


def get_create_loop():
    """
    Get or create the event loop. Works in another thread.
    """

    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        loop: asyncio.AbstractEventLoop | None = getattr(_LOCAL, "loop", None)
        if loop is None or loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            _LOCAL.loop = loop
        return _LOCAL.loop


async def async_run(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """
    Run sync function in a separate thread.
    * `func` - the function to run
    * `*args` - the arguments to pass to the function
    * `**kwargs` - the keyword arguments to pass to the function
    """

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, copy_context().run, partial(func, *args, **kwargs))


async def wait_until(Awaitable):
    """
    Wait until the given awaitable is done.

    Won't raise any exception.
    """
    flag = asyncio.Event()
    fut = asyncio.ensure_future(Awaitable)
    fut.add_done_callback(lambda _: flag.set())
    await flag.wait()


@overload
def select(awaitables: Sequence[Awaitable[T] | AsyncGenerator[T, Any]],
           return_future: Literal[True]
           ) -> AsyncGenerator[Future[T], None]:
    ...


@overload
def select(awaitables: Sequence[Awaitable[T] | AsyncGenerator[T, Any]],
           return_future: Literal[False] = False
           ) -> AsyncGenerator[T, None]:
    ...


async def select(awaitables: Sequence[Awaitable[T] | AsyncGenerator[T, Any]],
                 return_future=False):
    """
    similar to asyncio.as_completed but returns the results as they are done.

    If one of the tasks raised an exception, it will be raised by `select`
    if `return_future` is False, otherwise the future will be returned.

    * `awaitables` - the awaitables to wait for, can be `coroutine`, `future`,
     `AsyncGenerator`
    * `buffersize` - if > 0, the max number of results to buffer before yielding,
     this can prevent the generator from eating up RAM.
    * `return_future` - if True, the future will be returned instead of the
        result.

    Usage:
    ```
    async for result in select([func1(), func2(), func3()]):
        print(result)
    ```
    """

    async def _run(aw: Awaitable[T] | AsyncGenerator[T, Any]):
        if inspect.isasyncgen(aw):
            task = asyncio.create_task(aw.asend(None))
        else:
            aw = cast(Awaitable[T], aw)
            task = asyncio.ensure_future(aw)
        await wait_until(task)
        return (aw, task)

    loop = asyncio.get_running_loop()
    done = set[Task]()
    pending = set(loop.create_task(_run(aw)) for aw in awaitables)

    while pending:
        done, pending = await asyncio.wait(
            pending, return_when=asyncio.FIRST_COMPLETED)

        while done:
            aw, task = done.pop().result()
            exc = task.exception()

            if inspect.isasyncgen(aw):
                if exc is None:
                    pending.add(loop.create_task(_run(aw)))
                elif isinstance(exc, StopAsyncIteration):
                    continue
            try:
                if return_future:
                    yield task
                else:
                    yield task.result()
            except:
                for task in pending:
                    task.cancel()
                raise
