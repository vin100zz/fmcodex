def create_app(*args, **kwargs):
    from api.app import create_app as factory

    return factory(*args, **kwargs)

__all__ = ["create_app"]
