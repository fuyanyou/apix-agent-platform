import asyncio
import copy
import time

from enum import Enum

from apix_agent.commons.type_def import ApixEventEnvelope, MinimalEnvelopeData, ApixIdentity
from apix_agent.commons.logger import logger


class AgentCommonEvent(str, Enum):
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'


EVENT_PIPE = asyncio.Queue(maxsize=1000)
    

class EventPipeWriter:
    #发送事件到事件管道中，供其他组件消费。
    # 事件包括 INFO、WARNING、ERROR 等类型，包含目标接收者和数据内容。
    # 事件管道是一个异步队列，支持并发发送和接收事件。
    # 事件发送后，其他组件可以通过 get_event 方法获取事件，或者通过 clear 方法清空管道。
    # 事件发送时会记录日志
    # 事件发送时会记录日志，便于调试和监控。
    async def post_event(
        self,
        *,
        event: AgentCommonEvent,
        target: ApixIdentity = None,
        data: MinimalEnvelopeData = None,
        timestamp: float = None,
        generation_id: str = None
    ):
        '''
        Args:
            event: Event enum.
            target: Event receiver, the ApixEventEnvelope will try to send to this target at the final.
            data: Event data, should contains event_name and content.
        '''
        
        envelope: ApixEventEnvelope = {
            "event": event.value,
            "target": copy.deepcopy(target),
            "data": copy.deepcopy(data),
            "timestamp": timestamp or time.time(),
            "generation_id": generation_id,
            "blocking": False,
        }

        await EVENT_PIPE.put(envelope)

    async def get_event(self) -> ApixEventEnvelope:
        return await EVENT_PIPE.get()
    
    async def clear(self):
        count = 0
        while not EVENT_PIPE.empty():
            await EVENT_PIPE.get()
            count = count + 1

        logger.info(f"Cleaned {count} in pipe.")
        return count


#创建一个事件管道写入器实例，用于发送和接收事件。
event_pipe = EventPipeWriter()