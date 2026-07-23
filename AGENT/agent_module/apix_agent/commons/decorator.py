import inspect
from functools import wraps
#将函数装饰器应用于函数或类的__init__方法，
# 以忽略意外的关键字参数，从而提高代码的灵活性和容错性。
def accept_extra_kwargs(func):
    """
    Ignore unexpected keyword arguments.
    Works for functions and class __init__.
    """
    sig = inspect.signature(func)
    param_names = set(sig.parameters.keys())

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Filter out unexpected keyword arguments
        filtered_kwargs = {
            k: v for k, v in kwargs.items()
            if k in param_names
        }
        return func(*args, **filtered_kwargs)

    return wrapper
