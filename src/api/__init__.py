def create_app(*args, **kwargs):
    from api.app import create_app as factory

    return factory(*args, **kwargs)


from api.persistence import list_slots, load_session, save_session

__all__ = ["create_app", "list_slots", "load_session", "save_session"]
