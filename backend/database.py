
from pymongo import MongoClient

# ======================================
# STEP 1: Connect to MongoDB
# ======================================

client = MongoClient(
    "mongodb://localhost:27017/",
    serverSelectionTimeoutMS=5000
)

# Select database and collection
db = client["procurement_ai"]
collection = db["purchase_orders"]

try:
    # ======================================
    # STEP 2: Test database connection
    # ======================================

    client.admin.command("ping")
    print("MongoDB connected successfully!")

    # ======================================
    # STEP 3: Count purchase records
    # ======================================

    total_records = collection.count_documents({})

    print(f"Total records: {total_records:,}")

    # ======================================
    # STEP 4: Calculate total spending
    # ======================================

    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_spending": {
                    "$sum": "$total_price_numeric"
                }
            }
        }
    ]

    result = list(collection.aggregate(pipeline))

    total_spending = (
        result[0]["total_spending"] if result else 0
    )

    print(f"Total spending: ${total_spending:,.2f}")

except Exception as error:
    print(f"Error: {error}")

finally:
    client.close()
