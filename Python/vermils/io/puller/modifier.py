import rich.progress
import asyncio
from typing import Callable
from .pullers import BasePuller, AsyncPuller, AsyncWorker, Response
from ...gadgets import to_ordinal
from ...asynctools import ensure_async
from ...gadgets.sidelogging import LoggerLike


class Modifier:
    progress = None

    @classmethod
    def show_progress(
        cls,
        puller: BasePuller,
        desc_len: int = 24,
        delay_on_finish: float | None = 0.5,
        progress: rich.progress.Progress | None = None,
    ) -> None:
        """
        ### Show progress of all tasks.
        * `puller`: Puller instance
        * `desc_len`: max length of url description
        * `delay_on_finish`: time to remove finished progress bar, set to `None` to keep it
        * `progress`: rich.progress.Progress instance, set to `None` to use default one
        """
        from rich.progress import Progress
        if cls.progress is None:
            cls.progress = Progress(refresh_per_second=30)
        _progress = progress or cls.progress

        if isinstance(puller, AsyncPuller):
            @puller.on.worker.start
            async def create_task(event: str, worker: AsyncWorker):
                nonlocal puller
                progress = _progress  # In case outer progress is changed
                desc = worker.url.split("://")[-1]
                if len(desc) > desc_len:
                    desc = desc[:(desc_len-3)//2] + "..." + \
                        desc[-(desc_len-3)//2:]
                progress.start()  # start progress bar
                task = progress.add_task(desc)
                total = 0
                failed = False

                @worker.event_hooks.on.worker.response_get
                async def get_total(event: str, worker: AsyncWorker, r: Response):
                    nonlocal task
                    nonlocal total
                    total = int(r.headers.get("Content-Length", 0))
                    progress.update(task, total=total or 100)

                @worker.event_hooks.on.worker.bytes_get
                async def update_task(ev: str, w: AsyncWorker, r: Response, b: bytes):
                    nonlocal task
                    nonlocal total
                    if total:
                        progress.update(task, completed=r.num_bytes_downloaded)

                @worker.event_hooks.on.worker.fail
                async def fail_task(ev: str, w: AsyncWorker, e: Exception):
                    nonlocal failed
                    nonlocal task
                    failed = True
                    if isinstance(e, FileExistsError):
                        progress.remove_task(task)

                @worker.event_hooks.on.worker.destroy
                async def remove_task(event: str, worker: AsyncWorker):
                    nonlocal task
                    nonlocal total
                    if not failed:
                        if not total:  # Show completed for unknown size
                            progress.update(task, total=1, completed=1)
                        progress.refresh()
                        if delay_on_finish is not None:
                            await asyncio.sleep(delay_on_finish)
                            progress.update(task, visible=False, refresh=True)
                            progress.remove_task(task)
                    if progress.finished:
                        progress.stop()

    @staticmethod
    def ignore_failure(puller: BasePuller) -> None:
        """
        ### Ignore all exceptions.
        * `puller`: Puller instance
        """
        if isinstance(puller, AsyncPuller):
            @puller.on.worker.fail
            async def ignore_failure(event: str, worker: AsyncWorker, e: Exception):
                return True

    @staticmethod
    def ignore_file_exists(puller: BasePuller) -> None:
        """
        ### Ignore `FileExistsError`.
        * `puller`: Puller instance
        """
        if isinstance(puller, AsyncPuller):
            @puller.on.worker.fail
            async def ignore_file_exists(event: str, worker: AsyncWorker, e: Exception):
                if isinstance(e, FileExistsError):
                    return True

    @staticmethod
    def raise_for_status(puller: BasePuller) -> None:
        """
        ### Raise exception on non-200 status.
        * `puller`: Puller instance
        """
        if isinstance(puller, AsyncPuller):
            @puller.on.worker.response_get
            async def raise_for_status(event: str, worker: AsyncWorker, r: Response):
                r.raise_for_status()

    @staticmethod
    def add_logging(puller: BasePuller, logger: LoggerLike) -> None:
        """
        ### Add logging for events.
        * `puller`: Puller instance
        * `logger`: logger-like instance
        """
        if isinstance(puller, AsyncPuller):
            @puller.on.puller.spawn
            async def p_log_spawn(event: str, puller: AsyncPuller):
                logger.debug(f"Puller spawned. {puller}")

            @puller.on.puller.join
            async def p_log_join(event: str, puller: AsyncPuller):
                logger.debug(f"Puller joined. {puller}")

            @puller.on.puller.destroy
            async def p_log_destroy(event: str, puller: AsyncPuller):
                logger.debug(f"Puller destroyed. {puller}")

            @puller.on.worker.spawn
            async def log_spawn(event: str, worker: AsyncWorker):
                logger.debug(f"Spawned worker {worker}")

            @puller.on.worker.start
            async def log_start(event: str, worker: AsyncWorker):
                logger.debug(f"Start: {worker}")

            @puller.on.worker.response_get
            async def log_response(event: str, worker: AsyncWorker, r: Response):
                logger.debug(f"Response: {r.status_code}  {r.url}")

            @puller.on.worker.bytes_get
            async def log_bytes(event: str, worker: AsyncWorker, r: Response, b: bytes):
                logger.debug(f"Bytes size: {len(b)} from {r.url}")

            @puller.on.worker.retry
            async def log_retry(event: str, worker: AsyncWorker, e: Exception, retry: int):
                logger.debug(f"Retry: {worker} at {to_ordinal(retry)} time")

            @puller.on.worker.destroy
            async def log_destroy(event: str, worker: AsyncWorker):
                logger.debug(f"Destroy: {worker}")

            @puller.on.worker.fail
            async def log_fail(event: str, worker: AsyncWorker, e: Exception):
                logger.error(f"Fail: {worker} due to {type(e).__name__}: {e}")
                logger.exception(e, exc_info=e)

    @staticmethod
    def on_every_event(puller: BasePuller, func: Callable) -> None:
        """
        ### Call function on every event.
        * `puller`: Puller instance
        * `func`: function to call
        """
        if isinstance(puller, AsyncPuller):
            @puller.on.puller.spawn
            @puller.on.puller.join
            @puller.on.puller.destroy
            @puller.on.worker.spawn
            @puller.on.worker.start
            @puller.on.worker.response_get
            @puller.on.worker.bytes_get
            @puller.on.worker.retry
            @puller.on.worker.destroy
            @puller.on.worker.fail
            async def on_every_event(*args, **kw):
                await ensure_async(func)(*args, **kw)
