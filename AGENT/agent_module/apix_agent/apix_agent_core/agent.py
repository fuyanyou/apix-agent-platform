import traceback
from typing import AsyncIterator, Any
import time
import asyncio

from langgraph.graph.state import CompiledStateGraph

from apix_agent.commons.auto_init import auto_init
from apix_agent.apix_agent_core.agent_factory.agent_creator import agent_creator
from apix_agent.apix_agent_core.agent_task.team_task_manager import team_task_manager
from apix_agent.commons.type_def import MainAgentState, SubAgentState, AgentConfigSchema
from apix_agent.commons.logger import logger
#agent运行时 AgentRuningtime 是一个管理子助手任务的类，提供了启动、停止、提交和管理子助手任务的功能。
class AgentRuningtime:

    def __init__(self):
        # Sub-agent worker
        self._sub_agent_worker_task: asyncio.Task | None = None
        self._sub_agent_stop_task: asyncio.Task | None = None
        self._running_tasks: dict[str, asyncio.Task] = {}

        self.agent_config: dict = {}
    
    #-----------------------------------------------------------------------
    # Lifespan
    #-----------------------------------------------------------------------

    async def start(self):
        """
        Start background tasks.
        Safe to call multiple times.
        """
#启动后，两个协程在后台永久运行：


# sub-agent-worker 循环:
#   while True:
#     agent_name, initial_state, config = await team_task_manager.task_queue.get()
#     # ↑ 阻塞等待，有任务来才继续
#     task = asyncio.create_task(self._run_sub_agent(...))
#     self._running_tasks[task_id] = task

# sub-agent-stopper 循环:
#   while True:
#     task_id = await team_task_manager.stop_request_queue.get()
#     # ↑ 阻塞等待，有停止请求才继续
#     task = self._running_tasks.get(task_id)
#     task.cancel()  # 发送 CancelledError 到子Agent协程
# 为什么 start() 可以被多次调用而不出问题？ 因为有 if ... is None 判断。
# FastAPI 在多 worker 模式下可能会多次触发 lifespan，
# 这个防御避免了创建重复的协程

        if self._sub_agent_stop_task is None:
            self._sub_agent_stop_task = asyncio.create_task(
                #创建子任务停止器后台协程
                self.stop_sub_agent(),
                name="sub-agent-stopper",
            )

        if self._sub_agent_worker_task is None:
            #创建子任务调度器后台携程
            self._sub_agent_worker_task = asyncio.create_task(
                self._sub_agent_worker_loop(),
                name="sub-agent-worker",
            )
            logger.info("Worker started.")


    async def stop(self):
        """
        Stop background tasks gracefully.
        """

        # Stop sub-agent stopper
        stopper = self._sub_agent_stop_task
        if stopper:
            self._sub_agent_stop_task = None
            stopper.cancel()
            try:
                await stopper
            except asyncio.CancelledError:
                pass

        # Stop sub-agent worker
        worker = self._sub_agent_worker_task
        if worker:
            self._sub_agent_worker_task = None
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass
            logger.info("Worker stopped.")


    async def _run_sub_agent(
        self,
        agent_name: str,
        initial_state: SubAgentState,
        config: AgentConfigSchema,
    ):
        """
        Execute one sub-agent task.

        This runs in its own asyncio Task so multiple
        sub-agents can run concurrently.
        """
        agent = None

        try:

            agent = await agent_creator.create_sub_agent(agent_name, initial_state.get("agent_role"), config)

            if not isinstance(agent, CompiledStateGraph):
                logger.error(f"Create sub-agent failed: {agent}")
                return
            
            stream = agent.astream(
                initial_state,
                {"recursion_limit": 1024},
                stream_mode="custom",
            )

            await team_task_manager.mark_in_progress(initial_state["history_id"], initial_state["task_id"])

            async for chunk in stream:
                if chunk.get("event") == "tool_exec_start":
                    tool_data = chunk.get("data", {})
                    if tool_data.get("tool_name", "") == "write_todos":
                        await team_task_manager.update_task_state_store(initial_state["history_id"], initial_state["task_id"], todos=tool_data.get("content", []))
                elif chunk.get("event") == "ai_message_return":
                    msg_data = chunk.get("data", {})
                    if msg_data.get("event_name", "") == "output_chunk_rtn":
                        await team_task_manager.update_task_state_store(initial_state["history_id"], initial_state["task_id"], outputs=msg_data.get("content", ""))

            await team_task_manager.mark_completed(initial_state["history_id"], initial_state["task_id"])

        except asyncio.CancelledError:
            await team_task_manager.mark_cancelled(initial_state["history_id"], initial_state["task_id"])
            logger.info(f"Task stopped: {initial_state['task_id']}")

        except Exception as e:
            error_logs = traceback.format_exc()
            await team_task_manager.mark_failed(initial_state["history_id"], initial_state["task_id"], error=f"{type(e)}: {e}: {error_logs}")
            logger.error(f"Task execution failed: {type(e)}: {e}: {error_logs}")

        finally:
            # Remove from running task registry
            self._running_tasks.pop(initial_state["task_id"], None)
            if agent:
                await agent_creator.done(agent)


    async def _sub_agent_worker_loop(self):
        """
        Background worker that dispatches sub-agent tasks.
        """
        try:
            while True:
                agent_name, initial_state, config = await team_task_manager.task_queue.get()

                try:
                    task_id = initial_state.get("task_id")

                    if not task_id:
                        logger.error("No task_id provided in initial_state.")
                        raise RuntimeError("No task_id provided in initial_state.")

                    # Dispatch task
                    task = asyncio.create_task(
                        self._run_sub_agent(
                            agent_name,
                            initial_state,
                            config,
                        )
                    )

                    self._running_tasks[task_id] = task

                finally:
                    team_task_manager.task_queue.task_done()

        except asyncio.CancelledError:
            logger.info("Worker loop task cancelled.")

    #停止子助手任务的后台工作器，监听停止请求队列，并取消对应的运行任务。
    async def stop_sub_agent(self):
        """
        Background worker that handles stop requests for running sub-agent tasks.
        """
        try:
            while True:
                task_id = await team_task_manager.stop_request_queue.get()

                task = self._running_tasks.get(task_id)

                if not task:
                    logger.warning(f"Task not found: {task_id}")
                    team_task_manager.stop_request_queue.task_done()
                    continue

                logger.info(f"Cancelling task: {task_id}")

                task.cancel()

                try:
                    await task
                except asyncio.CancelledError:
                    pass
                
                team_task_manager.stop_request_queue.task_done()

        except asyncio.CancelledError:
            logger.info("Stop sub-agent loop cancelled.")
            

    #---------------------------------------------------------------
    # Streaming task API
    #---------------------------------------------------------------
    #将提交的任务交给agent_creator创建一个新的agent实例，
    # 并返回一个异步迭代器，
    async def submit_agent_task(
        self,
        agent_role: MainAgentState | SubAgentState = None,
        agent_name: str = None,
        config: AgentConfigSchema = None,
    ) -> CompiledStateGraph:
        """
        Start a streaming agent execution.

        Args:
            initial_state: MainAgentState, TypedDict.
            config: dict, llm model config.

        Returns:
            Async iterator of LangGraph stream events.
        """
        logger.trace()

        agent = await agent_creator.create_agent(agent_name, agent_role, config)
        if not isinstance(agent, CompiledStateGraph):
            raise RuntimeError(
                f"Get agent error. Please make sure your config correct.\n\nDetail: {agent}"
            )
        logger.info(
            f"Start agent streaming: "
            f"{agent_role} - {agent_name}"
        )

        return agent
    
    
    async def done(self, agent_graph: CompiledStateGraph) -> None:
        """
        Mark a graph as done (no longer in active use).
        """
        if agent_graph:
            #将图形标记为完成状态，
            # 以便清理器在后续的清理操作中可以回收它们，
            # 释放内存和资源。
            await agent_creator.done(agent_graph)
    


ai_agent = AgentRuningtime()

auto_init.register(ai_agent)