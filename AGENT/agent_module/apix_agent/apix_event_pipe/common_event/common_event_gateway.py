import asyncio
import traceback

from apix_agent.apix_event_pipe.common_event.event_registry import ApixEventItem, EventRegistry, event_registry
from apix_agent.commons.logger import logger
from apix_agent.commons.type_def import ApixEventEnvelope
from apix_agent.apix_event_pipe.common_event.agent_event_writer import event_pipe
from apix_agent.apix_event_pipe.event_handler_base import EventHandler


# =========================
# Common Event Handler
# =========================
#非流式事件处理器 PipeEventHandler 继承自 EventHandler，用于处理事件管道中的事件。
class PipeEventHandler(EventHandler):

    def __init__(
        self,
        registry: EventRegistry,
    ):
        super().__init__()

        self._registry = registry

        self._event_consumer_task: asyncio.Task | None = None #事件消费者任务，用于从事件管道中获取事件并分发给注册的处理器。
        self._dispatch_tasks: set[asyncio.Task] = set()#任务集合，用于跟踪当前正在处理的事件分发任务。
        self._dispatch_semaphore: asyncio.Semaphore = None #信号量，用于限制同时处理的事件分发任务的数量，防止过多的并发导致资源耗
        self._dispatch_semaphore = asyncio.Semaphore(100)#信号量的初始值为 100，表示最多允许同时处理 100 个事件分发任务。


    async def start(self):
        """
        Start event consumer worker.
        Safe to call multiple times.
        """

        if self._event_consumer_task is None:
            self._event_consumer_task = asyncio.create_task(
                self._event_consumer_loop(),
                name="pipe-event-consumer",
            )

            logger.info("Worker started.")

    async def stop(self):
        """
        Stop event consumer worker.
        """
        task = self._event_consumer_task

        if task:
            self._event_consumer_task = None

            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

        dispatch_tasks = list(self._dispatch_tasks)

        for dispatch_task in dispatch_tasks:
            dispatch_task.cancel()

        if dispatch_tasks:
            await asyncio.gather(
                *dispatch_tasks,
                return_exceptions=True,
            )

        self._dispatch_tasks.clear()

        logger.info("Worker stopped.")
        

    # Consumer
    async def _event_consumer_loop(self):
        """
        Serial event consumer.
        """

        logger.info("Event loop started.")

        try:
            while True:
                event = await event_pipe.get_event()
                await self._dispatch_semaphore.acquire()
                task = asyncio.create_task(
                    self._dispatch_event(event),
                )

                self._dispatch_tasks.add(task)
                task.add_done_callback(
                    self._dispatch_tasks.discard
                )

        except asyncio.CancelledError:
            logger.info("Event loop cancelled.")

    async def _dispatch_event(
        self,
        event_envelope: ApixEventEnvelope,
    ) -> ApixEventEnvelope | None:
        """
        Dispatch event to registered handlers.
        """

        try:
            event_name = ((event_envelope.get("data", {}) or {}).get("event_name"))

            if not event_name:
                return None

            handlers = self._registry.get_handlers(event_name)

            if not handlers:
                return event_envelope

            event = ApixEventItem.from_envelope(event_envelope)
            error_occured = False

            for handler in handlers:
                error_occured = False
                try:
                    await asyncio.wait_for(
                        handler.callback(event),
                        timeout=handler.time_out,
                    )

                    if event.accepted:
                        break

                except TimeoutError:
                    logger.error(
                        f"Handler timeout: "
                        f"event={event_name}, "
                        f"handler={handler.callback.__name__}, "
                    )

                except Exception as e:
                    error_occured = True
                    logger.error(
                        f"Handler failed: "
                        f"event={event_name}, "
                        f"handler={handler.callback.__name__}, "
                        f"error={type(e).__name__}: {e}\n"
                        f"{traceback.format_exc()}"
                    )

                    if handler.stop_when_error:
                        break

                if handler.push_to_user and not error_occured:
                    if event and event.target:
                        self._send_envelope(
                            target=event.target,
                            envelope=event.to_envelope()
                        )

            event.accept()
            return event.to_envelope()

        except Exception as e:
            logger.error(
                f"Dispatch failed: "
                f"{type(e).__name__}: {e}\n"
                f"{traceback.format_exc()}"
            )

        finally:
            self._dispatch_semaphore.release()



pipe_event_handler = PipeEventHandler(event_registry)