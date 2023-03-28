"""Pullers Collection"""
# -*- coding: utf-8 -*-
from __future__ import annotations
import os
import asyncio
from asyncio import Future
from typing import Iterable, Mapping, Any, Callable, Awaitable, Sequence, TypeVar
from abc import abstractmethod
from httpx import Request, Response, Timeout
from ..misc import DummyAioFileStream as Dummyf
from ...io import aio
from ...collections import StrChain
from ...react import ActionChain, EventHook, EventHint as Hint
from httpx._types import HeaderTypes, ProxiesTypes, CookieTypes, QueryParamTypes
import httpx

__all__ = (
    "MaxRetryReached",
    "BasePuller",
    "BaseWorker",
    "BaseMaster",
    "AsyncPuller",
    "AsyncWorker",
    "AsyncMaster",
)


class MaxRetryReached(Exception):
    """Raised when the maximum number of retries is reached."""


class BasePuller:
    """Base class for pullers."""
    @property
    def event_hooks(self) -> EventHook:
        """Event hook for this puller."""
        raise NotImplementedError()

    @abstractmethod
    def pull(self, url: str, path: str) -> Any:
        """Pull the file from the url to the path."""


class BaseWorker:
    """Base class for workers."""


class BaseMaster:
    """Base class for masters."""


HttpActionType = Callable[[Request | Response], Awaitable]
ActionVar = TypeVar('ActionVar', bound=Callable)


class AsyncHttpActionChain(ActionChain[HttpActionType]):
    """Async Http Action Chain"""

    def __init__(self, actions: Iterable[HttpActionType] = None) -> None:
        super().__init__(actions=actions)


class AsyncPullerEventHook(EventHook):
    """Async Puller Event Hook"""

    def __init__(self, chain: Mapping[str, Iterable[Callable[..., Any]]] | None = None):
        self.hook("request", AsyncHttpActionChain())
        self.hook("response", AsyncHttpActionChain())
        self.hook("worker.spawn", ActionChain())
        self.hook("worker.destroy", ActionChain())
        self.hook("worker.start", ActionChain())
        self.hook("worker.response_get", ActionChain())
        self.hook("worker.bytes_get", ActionChain())
        self.hook("worker.retry", ActionChain())
        self.hook("worker.success", ActionChain())
        self.hook("worker.fail", ActionChain())
        self.hook("puller.spawn", ActionChain())
        self.hook("puller.destroy", ActionChain())
        self.hook("puller.join", ActionChain())
        EventHook.__init__(self, chain=chain)


class AsyncWorker(BaseWorker):
    def __init__(
        self,
        puller: AsyncPuller,
        url: str,
        path: str | None,
        retry: int,
        overwrite: bool,
        *,
        future: Future = None,
        timeout: Timeout | float | None,
        extra_headers: HeaderTypes | None,
        extra_params: QueryParamTypes | None,
        extra_cookies: CookieTypes | None,
        **kw
    ):
        self.puller = puller
        self.url = url
        self.path = path
        self.future: Future = future  # type: ignore[assignment]
        self.timeout = timeout
        self.max_retry = retry
        self.overwrite = overwrite
        self.extra_headers = extra_headers
        self.extra_params = extra_params
        self.extra_cookies = extra_cookies
        self.kw = kw
        self.event_hooks = AsyncPullerEventHook(
            self.puller.event_hooks)  # snapshot

    async def run(self):
        """Run the worker."""
        event_hooks = self.event_hooks
        try:
            await event_hooks.aemit("worker.start", self)
            if self.path and os.path.exists(self.path) and not self.overwrite:
                raise FileExistsError(f"{self.path} already exists")
            client = self.puller.client
            retry = 0
            while True:
                try:
                    # Open file in async mode, if path is None, write to void
                    async with aio.open(self.path, "wb") \
                            if self.path else Dummyf() as f:  # type: ignore
                        # Establish connection
                        async with client.stream(
                            method=self.kw.pop("method", "GET"),
                            url=self.url,
                            params=self.extra_params,
                            headers=self.extra_headers,
                            cookies=self.extra_cookies,
                            timeout=self.timeout or self.puller.client.timeout,
                            **self.kw
                        ) as r:
                            await event_hooks.aemit("worker.response_get", self, r)
                            # Iterate over response chunks
                            # 256KB
                            async for chunk in r.aiter_bytes(chunk_size=2**18):
                                await event_hooks.aemit(
                                    "worker.bytes_get", self, r, chunk)
                                await f.write(chunk)
                            await f.flush()
                            await event_hooks.aemit("worker.success", self, r)
                    # set result for placeholder
                    self.future.set_result(self.path)
                    self.puller._ft_map.pop(id(self.future))  # type: ignore
                    break  # Quit successfully
                # Retry on network IO error
                except (httpx.HTTPError, httpx.StreamError) as e:
                    retry += 1
                    if retry > self.max_retry:
                        raise MaxRetryReached(
                            f"Max retry reached: {retry} times") from e
                    await event_hooks.aemit("worker.retry", self, e, retry)
                    await asyncio.sleep(min(30, 1.7 ** retry))
        # Fatal Errors
        except (Exception, asyncio.CancelledError) as e:
            handled = await event_hooks.aemit("worker.fail", self, e)
            if True not in handled:
                self.future.set_exception(e)
                raise e
            self.puller._ft_map.pop(id(self.future))  # type: ignore
        finally:
            await event_hooks.aemit("worker.destroy", self)
            self.puller._workers.get_nowait()
            self.puller._workers.task_done()  # workers count - 1

    def __repr__(self) -> str:
        return f"AsynWorker({self.url}, {self.path})"


class AsyncMaster(BaseMaster):
    def __init__(self, puller: AsyncPuller):
        self.puller = puller

    async def run(self):
        """Run the master."""
        try:
            buffer = self.puller._buffer
            workers = self.puller._workers
            while True:
                worker = await buffer.get()
                if worker is None:  # Kill signal
                    buffer.task_done()
                    break
                await workers.put(worker)  # blocks when max_workers reached
                self.puller.loop.create_task(worker.run())
                buffer.task_done()
                await asyncio.sleep(self.puller.interval)  # sleep a while
        finally:
            self.puller._master = None  # Reset master


class AsyncPuller(BasePuller):
    """### Async Puller"""

    def __init__(
        self,
        *,
        headers: HeaderTypes = None,
        params: QueryParamTypes = None,
        proxies: ProxiesTypes = None,
        cookies: CookieTypes = None,
        event_hooks: Mapping[str, Sequence[Callable]] = None,
        interval: float = 0.0,
        max_workers: int = 8,
        timeout: Timeout | float | None = 10,
        retry: int = 3,
        overwrite: bool = False,
        loop: asyncio.AbstractEventLoop = None,
        **kw
    ):
        """### Init Puller
        * `headers`: Default headers for all requests
        * `params`: Default query params for all requests
        * `proxies`: Default proxies for all requests
        * `cookies`: Default cookies for all requests
        * `event_hooks`: dict[str, Iterable[Callable]]
        * `interval`: Interval between each request
        * `max_workers`: Max downloading threads count
        * `timeout`: Timeout for each request
        * `retry`: Max retry times for each request
        * `overwrite`: Overwrite existing files
        * `loop`: Event loop
        * `**kw`: Other keyword arguments for httpx.Client
        """
        self._loop = loop
        self.interval = interval
        self.max_retry = max(retry, 0)
        self.overwrite = overwrite

        self._proxies = proxies
        self._master: AsyncMaster | None = None
        self._buffer: asyncio.Queue = asyncio.Queue()  # Pending workers
        self._workers: asyncio.Queue = asyncio.Queue(
            maxsize=max_workers)  # Running workers
        self._ft_map: dict[int, Future] = {}

        limits = httpx.Limits(
            max_connections=None,
            max_keepalive_connections=None,
            keepalive_expiry=10)

        self._client = httpx.AsyncClient(
            headers=headers,
            params=params,
            proxies=proxies,
            cookies=cookies,
            timeout=timeout,
            limits=limits,
            follow_redirects=True,
            http2=True,
            **kw
        )
        self.event_hooks = event_hooks or AsyncPullerEventHook()

        # Set up event hook
        def subscribe(event: StrChain, action: ActionVar) -> ActionVar:
            ev = str(event)
            self._event_hooks[ev].append(action)
            if ev in ["request", "response"]:
                self._client.event_hooks = self._event_hooks  # type: ignore[assignment]
            return action

        self._on = PullerEventHint(
            strchain=StrChain(joint='.', callback=subscribe))

    @property
    def client(self):
        return self._client

    @property
    def loop(self):
        if self._loop is None:
            self._loop = asyncio.get_running_loop()
        return self._loop

    @property
    def headers(self):
        """Get headers."""
        return self._client.headers

    @headers.setter
    def headers(self, value: HeaderTypes):
        """Set headers for all requests."""
        self._client.headers = value  # type: ignore[assignment]

    @property
    def cookies(self):
        return self._client.cookies

    @cookies.setter
    def cookies(self, value: CookieTypes):
        """Set cookies for all requests."""
        self._client.cookies = value  # type: ignore[assignment]

    @property
    def params(self):
        return self._client.params

    @params.setter
    def params(self, value: QueryParamTypes):
        """Set params for all requests."""
        self._client.params = value  # type: ignore[assignment]

    @property
    def event_hooks(self):
        return self._event_hooks

    @event_hooks.setter
    def event_hooks(self, hooks: Mapping[str, Sequence[Callable]]):
        """Set event hooks for all requests."""
        self._event_hooks = AsyncPullerEventHook(hooks)  # deepcopy
        self._client.event_hooks = self._event_hooks  # type: ignore[assignment]

    @property
    def on(self):
        """Shortcut for `Puller.event_hooks.on`"""
        return self._on

    @property
    def proxies(self):
        return self._proxies

    async def pull(
        self,
        url: str,
        path: str | None,
        *,
        extra_headers: HeaderTypes | None = None,
        extra_params: QueryParamTypes | None = None,
        extra_cookies: CookieTypes | None = None,
        timeout: Timeout | float | None = 0,
        retry: int | None = None,
        overwrite: bool | None = None,
        **kw
    ) -> Future:
        """
        ### Asynchronously pull a file from a url.
        File will be decompressed and saved in binary mode.

        Returns a `Future` instance refer to the path of the downloaded file.
        * `url`: url to pull from
        * `path`: path to save to, set to `None` or `""` will not save file

        Optional Parameters:
        * `extra_headers`: extra headers to add to request
        * `extra_params`: extra params to add to request
        * `extra_cookies`: extra cookies to add to request
        * `timeout`: timeout for this request, set to None will be no limit, 0 for default
        * `retry`: retry times for this request, set to None will use default
        * `overwrite`: overwrite file if exists, set to None will use default
        * `**kw`: extra keyword arguments for httpx.stream
        """
        timeout = self.client.timeout if timeout == 0 else timeout
        self._loop = self.loop or asyncio.get_running_loop()
        if self._master is None:
            self._master = AsyncMaster(self)
            self._loop.create_task(self._master.run())
        future: Future = Future()  # A placeholder for the worker.run() task
        self._ft_map[id(future)] = future
        worker = AsyncWorker(
            self,
            url=url,
            path=path,
            extra_headers=extra_headers,
            extra_params=extra_params,
            extra_cookies=extra_cookies,
            future=future,
            timeout=timeout,
            retry=self.max_retry if retry is None else retry,
            overwrite=overwrite or self.overwrite,
            **kw
        )
        await self._event_hooks.aemit("worker.spawn", worker)
        await self._buffer.put(worker)
        return future

    async def join(self) -> None:
        """### Wait for all workers to finish."""
        await self._event_hooks.aemit("puller.join", self)
        await self._buffer.join()  # Make sure no pending tasks
        await self._workers.join()  # Make sure all workers finished
        jobs = list(self._ft_map.values())
        self._ft_map.clear()
        await asyncio.gather(*jobs)  # Make sure all tasks are done

    async def aclose(self):
        await self.join()  # Make sure all tasks are done
        await self._buffer.put(None)  # Kill master
        await self._event_hooks.aemit("puller.destroy", self)
        await self._client.aclose()

    async def __aenter__(self) -> AsyncPuller:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        await self.aclose()
        return False

    def __repr__(self):
        return f"{self.__class__.__name__}:\n" +\
            f"  max_retry: {self.max_retry}\n" +\
            f"  overwrite: {self.overwrite}\n" +\
            f"  headers: {self.headers}\n" +\
            f"  params: {self.params}\n" +\
            f"  cookies: {self.cookies}\n" +\
            f"  proxies: {self.proxies}\n" +\
            f"  event_hooks: {self.event_hooks}\n"


#### Start Hinting: Add hints for event names ####

class on_puller_hint(Hint):  # pragma: no cover
    @property
    def spawn(self):
        """Callback Type: (event_name: str, AsyncPuller) -> None"""
        return self._chain.spawn

    @property
    def destroy(self):
        """Callback Type: (event_name: str, AsyncPuller) -> None"""
        return self._chain.destroy

    @property
    def join(self):
        """Callback Type: (event_name: str, AsyncPuller) -> None"""
        return self._chain.join


class on_worker_hint(Hint):  # pragma: no cover
    @property
    def spawn(self):
        """Callback Type: (event_name: str, AsyncWorker) -> None"""
    @property
    def destroy(self):
        """Callback Type: (event_name: str, AsyncWorker) -> None"""
    @property
    def start(self):
        """Callback Type: (event_name: str, AsyncWorker) -> None"""
    @property
    def response_get(self):
        """Callback Type: (event_name: str, AsyncWorker, Response) -> None"""
    @property
    def bytes_get(self):
        """Callback Type: (event_name: str, AsyncWorker, Response, bytes) -> None"""
    @property
    def retry(self):
        """Callback Type: (event_name: str, AsyncWorker, Exception, retry: int) -> None"""
    @property
    def success(self):
        """Callback Type: (event_name: str, AsyncWorker) -> None"""
    @property
    def fail(self):
        """Callback Type: (event_name: str, AsyncWorker, Exception) -> bool:
        whether to ignore the exception"""


class PullerEventHint(Hint):  # pragma: no cover
    """Puller Event Hint."""
    @property
    def puller(self) -> on_puller_hint:
        return self._chain.puller  # type: ignore

    @property
    def worker(self) -> on_worker_hint:
        return self._chain.worker  # type: ignore

    @property
    def request(self):
        """Callback Type: (Request) -> None"""
        return self._chain.request

    @property
    def response(self):
        """Callback Type: (Response) -> None"""
        return self._chain.response

### End Hinting ###
