
from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
collection = client["procurement_ai"]["purchase_orders"]

# =====================================
# TEST 1: TOP 5 SUPPLIERS
# =====================================

print("\nTOP 5 SUPPLIERS BY SPENDING")

pipeline = [
    {
        "$match": {
            "Supplier Name": {"$nin": [None, ""]}
        }
    },
    {
        "$group": {
            "_id": "$Supplier Name",
            "total_spending": {
                "$sum": "$total_price_numeric"
            }
        }
    },
    {"$sort": {"total_spending": -1}},
    {"$limit": 5}
]

for item in collection.aggregate(pipeline):
    print(
        item["_id"],
        f"${item['total_spending']:,.2f}"
    )

# =====================================
# TEST 2: TOP 5 DEPARTMENTS
# =====================================

print("\nTOP 5 DEPARTMENTS BY SPENDING")

pipeline = [
    {
        "$match": {
            "Department Name": {"$nin": [None, ""]}
        }
    },
    {
        "$group": {
            "_id": "$Department Name",
            "total_spending": {
                "$sum": "$total_price_numeric"
            }
        }
    },
    {"$sort": {"total_spending": -1}},
    {"$limit": 5}
]

for item in collection.aggregate(pipeline):
    print(
        item["_id"],
        f"${item['total_spending']:,.2f}"
    )

# =====================================
# TEST 3: SPENDING BY CALENDAR YEAR
# =====================================

print("\nSPENDING BY CALENDAR YEAR")

pipeline = [
    {
        "$match": {
            "creation_date_parsed": {
                "$type": "date"
            }
        }
    },
    {
        "$group": {
            "_id": {
                "$year": "$creation_date_parsed"
            },
            "total_spending": {
                "$sum": "$total_price_numeric"
            }
        }
    },
    {"$sort": {"_id": 1}}
]

for item in collection.aggregate(pipeline):
    print(
        item["_id"],
        f"${item['total_spending']:,.2f}"
    )

client.close()
