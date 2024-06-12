from modules.database import update_one, find_many

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
    users = find_many('users', {})
    for user in users:
        udata = {
            key: user[key] for key in user
        }
        cache[user['id']] = udata
