import pymongo

client = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
db = client["homestead"]


def find_one(collection, query):
    return db[collection].find_one(query)


def find_many(collection, query):
    return db[collection].find(query)


def insert_one(collection, data):
    return db[collection].insert_one(data)


def insert_many(collection, data):
    return db[collection].insert_many(data)


def update_one(collection, query, data, upsert=True):
    return db[collection].update_one(query, {'$set': data}, upsert)


def update_many(collection, query, data, upsert=True):
    return db[collection].update_many(query, {'$set': data}, upsert)


def delete_one(collection, query):
    return db[collection].delete_one(query)


def delete_many(collection, query):
    return db[collection].delete_many(query)
