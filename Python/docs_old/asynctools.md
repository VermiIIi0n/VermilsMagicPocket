
# Asynctools

## `vermils.asynctools.AsinkRunner`

This class is used to run asynchronous functions in a synchronous environment.

It runs sync-functions sequentially in another thread. Since it is a long-lived object,  
it's cheaper to create it once and use it multiple times than to create it every time  
using something like `threading.Thread` or `concurrent.futures.ThreadPoolExecutor`.

Also, it supports `concurrenct.futures.Future` objects, so you don't need `asyncio` to
use it.

```Python
import time
import asyncio
from vermils.asynctools.asinkrunner import AsinkRunner

runner = AsinkRunner()

def do_something():
    time.sleep(1)

sync_future = runner.sync_run(do_something)  # returns a concurrent.futures.Future

# Do something else

result = sync_future.result()  # Get the result of the sync function

async def main():
    await runner.run(do_something)  # returns an asyncio.Future

asyncio.run(main())
```

You can prioritize tasks by replacing `runner.sync_run` and `runner.run` with
`runner.sync_run_as` and `runner.run_as` respectively. The first argument is the
priority, and the second argument is the function to run.

```Python
import time
from vermils.asynctools.asinkrunner import AsinkRunner

runner = AsinkRunner()

def do_something(time_to_sleep):
    time.sleep(time_to_sleep)

sync_future = runner.sync_run_as(1, do_something, 10)  # sleep for 10 seconds

sync_future2 = runner.sync_run_as(0, do_something, 1)  # sleep for 1 second

sync_future3 = runner.sync_run_as(2, do_something, 5)  # sleep for 5 seconds

# sync_future will be done first, then sync_future3, then sync_future2
```
