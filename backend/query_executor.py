
from datetime import datetime, timezone
from pymongo import MongoClient

# ==========================================
# DATABASE CONNECTION
# ==========================================

client = MongoClient(
    "mongodb://localhost:27017/",
    serverSelectionTimeoutMS=5000
)

collection = client["procurement_ai"]["purchase_orders"]


# ==========================================
# EXECUTE VALIDATED QUERY PLAN
# ==========================================

def execute_plan(plan):

    analysis = plan["analysis"]

    year = plan.get("year")
    month = plan.get("month")
    quarter = plan.get("quarter")

    supplier = plan.get("supplier")
    department = plan.get("department")

    limit = plan.get("limit", 5)

    allowed = {
        "total_spending",
        "record_count",
        "top_suppliers",
        "top_departments",
        "top_items",
        "yearly_spending",
        "unique_order_count",
        "highest_spending_quarter",
        "most_frequent_items"
    }

    if analysis not in allowed:
        raise ValueError("Unsupported analysis")

    # --------------------------------------
    # VALIDATE YEAR
    # --------------------------------------

    if year is not None:
        if type(year) is not int or not 2012 <= year <= 2015:
            raise ValueError("Invalid year")

    # --------------------------------------
    # VALIDATE MONTH
    # --------------------------------------

    if month is not None:
        if type(month) is not int or not 1 <= month <= 12:
            raise ValueError("Invalid month")

    # --------------------------------------
    # VALIDATE QUARTER
    # --------------------------------------

    if quarter is not None:
        if type(quarter) is not int or not 1 <= quarter <= 4:
            raise ValueError("Invalid quarter")

    if month is not None and quarter is not None:
        raise ValueError(
            "Month and quarter cannot be combined"
        )

    if (
        month is not None
        or quarter is not None
    ) and year is None:
        raise ValueError(
            "Month or quarter requires a year"
        )

    if analysis == "highest_spending_quarter":
        if month is not None or quarter is not None:
            raise ValueError(
                "Highest-spending-quarter analysis "
                "cannot use a month or quarter filter"
            )

    # --------------------------------------
    # VALIDATE LIMIT
    # --------------------------------------

    if type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError("Invalid limit")

    # --------------------------------------
    # BUILD MONGODB FILTERS
    # --------------------------------------

    filters = {}

    # --------------------------------------
    # YEAR / MONTH / QUARTER FILTERING
    # --------------------------------------

    if year is not None:

        if month is not None:
            start_month = month
            end_month = month + 1

        elif quarter is not None:
            start_month = (quarter - 1) * 3 + 1
            end_month = start_month + 3

        else:
            start_month = 1
            end_month = 13

        start_date = datetime(
            year,
            start_month,
            1,
            tzinfo=timezone.utc
        )

        if end_month > 12:

            end_date = datetime(
                year + 1,
                end_month - 12,
                1,
                tzinfo=timezone.utc
            )

        else:

            end_date = datetime(
                year,
                end_month,
                1,
                tzinfo=timezone.utc
            )

        filters["creation_date_parsed"] = {
            "$gte": start_date,
            "$lt": end_date
        }

    # --------------------------------------
    # SUPPLIER FILTER
    # --------------------------------------

    if supplier is not None:

        if (
            not isinstance(supplier, str)
            or not supplier.strip()
        ):
            raise ValueError("Invalid supplier")

        filters["Supplier Name"] = supplier

    # --------------------------------------
    # DEPARTMENT FILTER
    # --------------------------------------

    if department is not None:

        if (
            not isinstance(department, str)
            or not department.strip()
        ):
            raise ValueError("Invalid department")

        filters["Department Name"] = department

    # --------------------------------------
    # TOTAL SPENDING
    # --------------------------------------

    if analysis == "total_spending":

        pipeline = [
            {"$match": filters},
            {"$group": {
                "_id": None,
                "total": {
                    "$sum": "$total_price_numeric"
                }
            }}
        ]

        rows = list(collection.aggregate(pipeline))

        return {
            "total_spending": round(
                rows[0]["total"], 2
            ) if rows else 0
        }

    # --------------------------------------
    # RECORD COUNT
    # --------------------------------------

    if analysis == "record_count":

        return {
            "record_count": collection.count_documents(
                filters
            )
        }

    # --------------------------------------
    # UNIQUE PURCHASE ORDER COUNT
    # --------------------------------------

    if analysis == "unique_order_count":

        match_filters = dict(filters)

        match_filters["Purchase Order Number"] = {
            "$exists": True,
            "$nin": [None, ""]
        }

        pipeline = [
            {"$match": match_filters},
            {"$group": {
                "_id": "$Purchase Order Number"
            }},
            {"$count": "unique_orders"}
        ]

        rows = list(collection.aggregate(
            pipeline,
            allowDiskUse=True
        ))

        return {
            "unique_order_count": (
                rows[0]["unique_orders"]
                if rows else 0
            )
        }

    # --------------------------------------
    # TOP SUPPLIERS / DEPARTMENTS / ITEMS
    # --------------------------------------

    group_fields = {
        "top_suppliers": "Supplier Name",
        "top_departments": "Department Name",
        "top_items": "Item Name"
    }

    if analysis in group_fields:

        field = group_fields[analysis]

        match_filters = dict(filters)

        match_filters[field] = {
            "$nin": [None, ""]
        }

        pipeline = [
            {"$match": match_filters},
            {"$group": {
                "_id": f"${field}",
                "spending": {
                    "$sum": "$total_price_numeric"
                }
            }},
            {"$sort": {
                "spending": -1,
                "_id": 1
            }},
            {"$limit": limit}
        ]

        rows = collection.aggregate(pipeline)

        return [
            {
                "name": str(row["_id"]),
                "spending": round(
                    row["spending"], 2
                )
            }
            for row in rows
        ]

    # --------------------------------------
    # MOST FREQUENTLY ORDERED ITEMS
    # --------------------------------------

    if analysis == "most_frequent_items":

        match_filters = dict(filters)

        match_filters["Item Name"] = {
            "$nin": [None, ""]
        }

        pipeline = [
            {"$match": match_filters},
            {"$group": {
                "_id": "$Item Name",
                "frequency": {"$sum": 1}
            }},
            {"$sort": {
                "frequency": -1,
                "_id": 1
            }},
            {"$limit": limit}
        ]

        rows = collection.aggregate(
            pipeline,
            allowDiskUse=True
        )

        return [
            {
                "name": str(row["_id"]),
                "frequency": row["frequency"]
            }
            for row in rows
        ]

    # --------------------------------------
    # HIGHEST-SPENDING QUARTER
    # --------------------------------------

    if analysis == "highest_spending_quarter":

        match_filters = dict(filters)

        if year is None:
            match_filters["creation_date_parsed"] = {
                "$type": "date"
            }

        pipeline = [
            {"$match": match_filters},
            {"$group": {
                "_id": {
                    "year": {
                        "$year": "$creation_date_parsed"
                    },
                    "quarter": {
                        "$ceil": {
                            "$divide": [
                                {
                                    "$month": "$creation_date_parsed"
                                },
                                3
                            ]
                        }
                    }
                },
                "spending": {
                    "$sum": "$total_price_numeric"
                }
            }},
            {"$sort": {
                "spending": -1,
                "_id.year": 1,
                "_id.quarter": 1
            }},
            {"$limit": 1}
        ]

        rows = list(collection.aggregate(
            pipeline,
            allowDiskUse=True
        ))

        if not rows:
            return None

        row = rows[0]

        return {
            "year": row["_id"]["year"],
            "quarter": row["_id"]["quarter"],
            "spending": round(
                row["spending"], 2
            )
        }

    # --------------------------------------
    # YEARLY SPENDING
    # --------------------------------------

    if analysis == "yearly_spending":

        match_filters = dict(filters)

        if year is None:
            match_filters["creation_date_parsed"] = {
                "$type": "date"
            }

        pipeline = [
            {"$match": match_filters},
            {"$group": {
                "_id": {
                    "$year": "$creation_date_parsed"
                },
                "spending": {
                    "$sum": "$total_price_numeric"
                }
            }},
            {"$sort": {
                "_id": 1
            }}
        ]

        rows = collection.aggregate(pipeline)

        return [
            {
                "year": row["_id"],
                "spending": round(
                    row["spending"], 2
                )
            }
            for row in rows
        ]
