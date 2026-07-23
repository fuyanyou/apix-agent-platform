from typing import Any, List

from apix_agent.commons.logger import logger

#自动初始化模块，负责管理全局生命周期服务的注册、启动和停止
class AutoInit:
    """
    Global auto initializer (singleton).

    Registered objects must implement:
        - async start(...)
        - async stop(...)
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Avoid reinitializing singleton
        if getattr(self, "_initialized", False):
            return

        self._services: List[Any] = []
        self._started = False
        self._initialized = True

    # -----------------------------
    # Registration
    # -------   ----------------------
    #将生命周期服务注册到自动初始化器中，以便在应用启动和停止时统一管理和调用。
    def register(self, service: Any):
        """
        Register a lifecycle service.

        Service must provide:
            - start()
            - stop()
        """
        if service in self._services:
            return

        if not hasattr(service, "start"):
            raise AttributeError(
                f"{service.__class__.__name__} missing start() method"
            )

        if not hasattr(service, "stop"):
            raise AttributeError(
                f"{service.__class__.__name__} missing stop() method"
            )

        self._services.append(service)

        logger.debug(
            f"Registered service: {service.__class__.__name__}"
        )

    # -----------------------------
    # Lifecycle
    # -----------------------------

    async def start(self):
        """
        Start all registered services once.
        """
        if self._started:
            return

        self._started = True

        if not self._services:
            logger.debug("No services")
            return

        logger.info("Starting...")

        for service in self._services:
            try:
                #调用对应服务的start方法
                await service.start()

                logger.debug(
                    f"Started: {service.__class__.__name__}"
                )

            except Exception as e:
                logger.exception(
                    f"Error starting "
                    f"{service.__class__.__name__}: {e}"
                )

        logger.success("All services started")

    async def stop(self):
        """
        Stop all registered services in reverse order.
        """
        if not self._services:
            logger.debug("No services")
            return

        logger.info("Stopping...")

        for service in reversed(self._services):
            try:
                await service.stop()

                logger.debug(
                    f"Stopped: {service.__class__.__name__}"
                )

            except Exception as e:
                logger.exception(
                    f"Error stopping "
                    f"{service.__class__.__name__}: {e}"
                )

        logger.success("All services stopped")

        self._started = False


auto_init = AutoInit()  
#auto_init会在python导入模块时，register（）被执行，然后把对象加入service列表，
#然后给整个系统导入5个服务，
# 1.agentruningtime Agent运行管理器，start调用_sub_agent_worker_loop 创建sub-agent-worker 后台协程
#子代理循环
#2. ResourceCleaner 资源清理器，创建 resource-cleaner 后台协程
# 3. DefaultPlatform websocket平台，为所有已连接用户的 sender_loop 启动协程
# AgentSandboxManager Docker管理 pass (无实际操作)
#  5.McpManager Mcp资源管理器，始化 MCP 客户端缓存
#然后会在FastApi lifeSpan进行全部启动和全部管理，main.py 文件中，