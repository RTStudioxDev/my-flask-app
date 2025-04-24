# def example_function():
#     return "This is a query function"

from pymongo import MongoClient
client = MongoClient('mongodb_uri')
db = client['finance_web_app']

db.transactions.update_many(
    {'mobile_deposit': {'$exists': False}},
    {'$set': {
        'mobile_deposit': 0,
        'commission': 0,
        'bonus': 0,
        'transfer': 0,
        'db': 0
    }})