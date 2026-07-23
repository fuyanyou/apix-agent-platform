from datetime import datetime
from typing import Literal
import inflect

#将当前日期转换为自然语言格式，便于在消息中显示。
def get_date_natural_language():
    now = datetime.now()
    
    day = now.day
    month = now.strftime("%B")
    year = now.year
    weekday = now.strftime("%A")
    
    p = inflect.engine()
    ordinal_day = p.ordinal(day)
    
    # "Wednesday, April 15th, 2026"
    natural_date = f"DATE: {weekday}, {month} {ordinal_day}, {year}"
    
    return natural_date

#将生成ID转换为消息节点ID，便于在数据库中存储和检索消息上下文。
def convert_generation_id_to_message_node_id(
    generation_id: str | list[str] | set[str],
    role: Literal['user', 'human', 'ai', 'assistant']
) -> str | list[str] | set[str]:
    suffix = "-user" if role in ['user', 'human'] else "-apix"

    def convert(gid: str) -> str:
        return gid[-12:] + suffix

    if isinstance(generation_id, str):
        return convert(generation_id)

    return type(generation_id)(
        convert(gid)
        for gid in generation_id
    )