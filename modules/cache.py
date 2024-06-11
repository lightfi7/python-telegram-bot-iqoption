from modules.database import update_one

cache = {}


def cached(key, data):
    if key in cache:
        return cache[key]
    cache[key] = data
    update_one('users', {'id': key}, data)
    return data


def cache_up(key, data):
    cache[key] = data
    update_one('users', {'id': key}, data)
    return data


def cache_down(key):
    cache[key] = None
    del cache[key]


def init():
    cache['users'] = {}
