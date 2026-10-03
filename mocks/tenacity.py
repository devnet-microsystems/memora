def retry(*args, **kwargs):
    def decorator(func):
        return func
    return decorator
def stop_after_attempt(*args, **kwargs):
    pass
def wait_exponential(*args, **kwargs):
    pass
