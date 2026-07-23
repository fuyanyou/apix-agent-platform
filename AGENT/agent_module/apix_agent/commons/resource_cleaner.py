import asyncio
import time
from typing import Callable, List, Awaitable, Union, Optional
from functools import wraps


from apix_agent.commons.auto_init import auto_init
from apix_agent.commons.logger import logger
from apix_agent.global_config import CACHE_CLEAN_INTERVAL

#将资源清理器设计为单例模式，提供集中化的清理调度和管理功能，
# 支持异步和同步的清理函数注册和执行，并在应用生命周期内自动启动和停止。
class ResourceCleaner:
    """
    Global resource cleaner (singleton).

    Features:
        - Centralized cleanup scheduler
        - Supports async / sync cleanup functions
        - Auto registration via decorator
        - Fault isolation between cleanup tasks
    """

    _instance = None

    def __new__(cls):
        # Singleton
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Registered cleanup functions
        self._cleaners: List[Callable[[], Union[int, Awaitable[int]]]] = []

        # Background task
        self._task: Optional[asyncio.Task] = None

        # Default interval (seconds)
        self._interval = CACHE_CLEAN_INTERVAL

        # Running flag
        self._running = False

    # -----------------------------
    # Registration
    # -----------------------------
    #将清理函数注册到资源清理器中，以便在后台循环中定期执行清理操作，支持异步和同步函数。
    def register(self, func: Callable):
        """
        Register a cleanup function manually.

        Args:
            func: Function returning int or Awaitable[int]
        """
        if func not in self._cleaners:
            self._cleaners.append(func)
            logger.debug(f"Registered: {func.__name__}")
    #将清理函数注册为装饰器，以便在定义函数时自
    # 动注册到资源清理器中，简化清理函数的管理和使用。
    def auto_clear(self, func: Callable):
        """
        Decorator to auto-register a cleanup function.

        Usage:
            @cleaner.auto_clear
            async def clean_xxx():
                return removed_count
        """

        self.register(func)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        return wrapper

    # -----------------------------
    # Lifecycle
    # -----------------------------

    async def start(self):
        """
        Start background cleanup loop.

        Args:
            interval: Cleanup interval in seconds
        """
        interval = CACHE_CLEAN_INTERVAL or 30

        if self._running:
            return

        self._interval = interval
        self._running = True

        self._task = asyncio.create_task(self._loop(), name="resource-cleaner")

        logger.info("Cleanup loop started")

    async def stop(self):
        """
        Stop background cleanup loop.
        """
        if not self._running:
            return

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

            self._task = None

        logger.info("Cleanup loop stopped")

    # -----------------------------
    # Core loop
    # -----------------------------
    #将后台循环作为异步任务运行，定期调用注册的清理函数，
    # 并处理异常和返回值，以便在应用运行期间持续进行资源清理。
    async def _loop(self):
        """
        Background loop.
        """
        try:
            while self._running:
                await asyncio.sleep(self._interval)
                await self.run_once()
        except asyncio.CancelledError:
            logger.debug("Cleanup loop cancelled")
    #将所有注册的清理函数执行一次，并统计总共清理的资源数量，
    async def run_once(self):
        """
        Execute all cleanup functions once.
        """
        if not self._cleaners:
            return

        total_removed = 0

        for func in list(self._cleaners):
            try:
                result = func()

                # Support async + sync
                if asyncio.iscoroutine(result):
                    result = await result

                if isinstance(result, int):
                    total_removed += result

            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")

        if total_removed:
            logger.info(f"Cleaned total={total_removed}")


# Global singleton
resource_cleaner = ResourceCleaner()

auto_init.register(resource_cleaner)