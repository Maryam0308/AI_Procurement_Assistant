
import os
import re
import json
import logging
from datetime import datetime, timezone
from fastapi.responses import FileResponse

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
from dotenv import load_dotenv
from google import genai

from .query_engine import understand_question
from .query_executor import execute_plan
from .insights_engine import generate_insights



# ==========================================
# CONFIGURATION
# ==========================================

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Procurement Assistant",
    description="California Procurement Analytics Chatbot",
    version="2.0"
)

mongo_client = MongoClient(
    "mongodb://localhost:27017/",
    serverSelectionTimeoutMS=5000
)

collection = mongo_client["procurement_ai"]["purchase_orders"]

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY is missing from .env")

ai_client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-3.8-flash"


class ChatRequest(BaseModel):
    question: str


# ==========================================
# DATABASE FUNCTIONS
# ==========================================

def total_spending():
    result = list(collection.aggregate([
        {"$group": {
            "_id": None,
            "total": {"$sum": "$total_price_numeric"}
        }}
    ]))
    return round(result[0]["total"], 2) if result else 0


def top_group(field, limit=5):
    pipeline = [
        {"$match": {
            field: {"$nin": [None, ""]}
        }},
        {"$group": {
            "_id": f"${field}",
            "spending": {"$sum": "$total_price_numeric"}
        }},
        {"$sort": {"spending": -1, "_id": 1}},
        {"$limit": limit}
    ]

    return [
        {
            "name": str(row["_id"]),
            "spending": round(row["spending"], 2)
        }
        for row in collection.aggregate(pipeline)
    ]


def spending_by_year(year=None):
    match = {
        "creation_date_parsed": {"$type": "date"}
    }

    if year is not None:
        match = {
            "creation_date_parsed": {
                "$gte": datetime(year, 1, 1, tzinfo=timezone.utc),
                "$lt": datetime(year + 1, 1, 1, tzinfo=timezone.utc)
            }
        }

    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": {"$year": "$creation_date_parsed"},
            "spending": {"$sum": "$total_price_numeric"}
        }},
        {"$sort": {"_id": 1}}
    ]

    return [
        {
            "year": row["_id"],
            "spending": round(row["spending"], 2)
        }
        for row in collection.aggregate(pipeline)
    ]


# ==========================================
# QUESTION UNDERSTANDING
# ==========================================

ALLOWED_INTENTS = {
    "TOTAL_SPENDING",
    "COUNT",
    "TOP_SUPPLIERS",
    "TOP_DEPARTMENTS",
    "YEARLY_SPENDING",
    "TOP_ITEMS",
    "TOP_ACQUISITION_TYPES",
    "UNSUPPORTED"
}


def classify_question(question):
    q = question.lower().strip()

    # Extract optional top-N ranking request.
    match = re.search(r"\btop\s+(\d+)\b", q)
    limit = min(max(int(match.group(1)), 1), 20) if match else 5

    # Extract calendar year.
    years = re.findall(r"\b20(?:12|13|14|15)\b", q)
    year = int(years[0]) if len(years) == 1 else None

    # Local recognition reduces Gemini API calls.
    if any(x in q for x in ["supplier", "vendor"]):
        intent = "TOP_SUPPLIERS"

    elif "department" in q:
        intent = "TOP_DEPARTMENTS"

    elif "acquisition type" in q:
        intent = "TOP_ACQUISITION_TYPES"

    elif any(x in q for x in ["item", "product"]):
        intent = "TOP_ITEMS"

    elif years or any(x in q for x in [
        "by year", "each year", "annual spending",
        "yearly spending", "spending trend"
    ]):
        intent = "YEARLY_SPENDING"

    elif (
        any(x in q for x in ["how many", "number", "count"])
        and any(x in q for x in ["record", "purchase", "entry"])
    ):
        intent = "COUNT"

    elif (
        any(x in q for x in ["spending", "spent", "expenditure"])
        and any(x in q for x in ["total", "overall", "all"])
    ):
        intent = "TOTAL_SPENDING"

    else:
        intent = "UNSUPPORTED"

    # Gemini can interpret questions not recognized locally.
    if intent == "UNSUPPORTED":
        try:
            response = ai_client.models.generate_content(
                model=MODEL_NAME,
                contents=f"""
Classify this procurement analytics question.

Allowed labels:
TOTAL_SPENDING - Total spending across all records
COUNT - Total number of records
TOP_SUPPLIERS - Rank suppliers by spending
TOP_DEPARTMENTS - Rank departments by spending
YEARLY_SPENDING - Spending by calendar year
TOP_ITEMS - Rank item names by spending
TOP_ACQUISITION_TYPES - Rank acquisition types by spending
UNSUPPORTED - Anything else

Return exactly one label, with no explanation.

Question: {question}
"""
            )

            candidate = (response.text or "").strip().upper()

            if candidate in ALLOWED_INTENTS:
                intent = candidate

        except Exception as error:
            logger.warning(
                "Gemini classification unavailable: %s",
                type(error).__name__
            )

    # Only execute the supported query shapes.
    # Avoid giving unfiltered answers to questions
    # requesting comparisons or unsupported filters.
    comparison = any(x in q for x in [
        "compare", "versus", " vs ", "between"
    ])

    if comparison and intent != "YEARLY_SPENDING":
        intent = "UNSUPPORTED"

    if len(years) > 1 and intent != "YEARLY_SPENDING":
        intent = "UNSUPPORTED"

    if years and intent not in [
        "YEARLY_SPENDING", "UNSUPPORTED"
    ]:
        intent = "UNSUPPORTED"

    return intent, limit, year


# ==========================================
# EXECUTE APPROVED QUERIES
# ==========================================

def execute_query(intent, limit, year):

    if intent == "TOTAL_SPENDING":
        return {
            "total_spending": total_spending(),
            "currency": "USD"
        }

    if intent == "COUNT":
        return {
            "total_records": collection.count_documents({})
        }

    if intent == "TOP_SUPPLIERS":
        return top_group("Supplier Name", limit)

    if intent == "TOP_DEPARTMENTS":
        return top_group("Department Name", limit)

    if intent == "TOP_ITEMS":
        return top_group("Item Name", limit)

    if intent == "TOP_ACQUISITION_TYPES":
        return top_group("Acquisition Type", limit)

    if intent == "YEARLY_SPENDING":
        return spending_by_year(year)

    return None


# ==========================================
# ANSWER GENERATION
# ==========================================

def format_fallback(intent, data):
    if intent == "TOTAL_SPENDING":
        return (
            "Total recorded procurement spending is "
            f"${data['total_spending']:,.2f}."
        )

    if intent == "COUNT":
        return (
            f"The database contains "
            f"{data['total_records']:,} procurement records."
        )

    if isinstance(data, list):
        if not data:
            return "No matching records were found."

        lines = []

        for row in data:
            name = row.get("name", row.get("year"))
            spending = row["spending"]
            lines.append(f"{name}: ${spending:,.2f}")

        return "\n".join(lines)

    return "The query completed."


def generate_answer(question, intent, data):
    fallback = format_fallback(intent, data)

    try:
        response = ai_client.models.generate_content(
            model=MODEL_NAME,
            contents=f"""
You are a California government procurement
data assistant.

Answer the question using ONLY the MongoDB
query results below.

Rules:
- Do not invent numbers or facts.
- Use USD for monetary values.
- Be concise and easy to understand.
- The records are procurement line items.
- Calendar year is based on Creation Date.
- Do not claim these represent unique orders.

Question:
{question}

MongoDB results:
{json.dumps(data, default=str)}
"""
        )

        if response.text:
            return response.text

    except Exception as error:
        logger.warning(
            "Gemini response unavailable: %s",
            type(error).__name__
        )

    return fallback


# ==========================================
# FASTAPI ENDPOINTS
# ==========================================

@app.get("/")
def home():
    return {
        "message": "AI Procurement Assistant API is running",
        "status": "success"
    }


@app.get("/summary")
def summary():
    try:
        return {
            "total_records": collection.count_documents({}),
            "total_spending": total_spending(),
            "currency": "USD"
        }
    except Exception as error:
        logger.exception("Summary error")
        raise HTTPException(
            status_code=500,
            detail="Database operation failed"
        ) from error





# ==========================================
# CHAT ENDPOINT
# ==========================================

@app.post("/chat")
def chat(request: ChatRequest):

    question = request.question.strip()

    # --------------------------------------
    # VALIDATE USER QUESTION
    # --------------------------------------

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )

    try:

        # --------------------------------------
        # STEP 1: UNDERSTAND USER QUESTION
        # --------------------------------------

        plan = understand_question(question)

        intent = plan["analysis"]

        # --------------------------------------
        # STEP 2: HANDLE UNSUPPORTED QUESTIONS
        # --------------------------------------

        if intent == "unsupported":

            return {
                "question": question,
                "intent": "UNSUPPORTED",
                "plan": plan,
                "data": None,
                "answer": (
                    "I couldn't interpret this question "
                    "with the currently supported analyses. "
                    "You can ask about procurement spending, "
                    "record counts, unique purchase orders, "
                    "top suppliers, departments, items, "
                    "yearly spending, highest-spending quarters, "
                    "and frequently ordered items."
                )
            }

        # --------------------------------------
        # STEP 3: EXECUTE MONGODB QUERY
        # --------------------------------------

        data = execute_plan(plan)

        # --------------------------------------
        # STEP 4: EXTRACT QUERY FILTERS
        # --------------------------------------

        year = plan.get("year")
        month = plan.get("month")
        quarter = plan.get("quarter")

        department = plan.get("department")
        supplier = plan.get("supplier")

        # --------------------------------------
        # STEP 5: BUILD FILTER DESCRIPTION
        # --------------------------------------

        context = []

        if month is not None and year is not None:

            from calendar import month_name

            context.append(
                f"in {month_name[month]} {year}"
            )

        elif quarter is not None and year is not None:

            context.append(
                f"in Q{quarter} {year}"
            )

        elif year is not None:

            context.append(
                f"in {year}"
            )

        if department:

            context.append(
                f"for {department}"
            )

        if supplier:

            context.append(
                f"for supplier {supplier}"
            )

        context_text = " ".join(context)

        # --------------------------------------
        # STEP 6: GENERATE ANSWER
        # --------------------------------------

        # TOTAL SPENDING
        if intent == "total_spending":

            amount = data["total_spending"]

            answer = (
                f"Total recorded procurement spending "
                f"{context_text} was ${amount:,.2f}."
            )

        # RECORD COUNT
        elif intent == "record_count":

            count = data["record_count"]

            answer = (
                f"There were {count:,} procurement "
                f"line-item records {context_text}."
            )

        # UNIQUE PURCHASE ORDER COUNT
        elif intent == "unique_order_count":

            count = data["unique_order_count"]

            answer = (
                f"There were {count:,} unique "
                f"purchase orders {context_text}."
            )

        # HIGHEST-SPENDING QUARTER
        elif intent == "highest_spending_quarter":

            if not data:

                answer = (
                    "No matching procurement records "
                    "were found."
                )

            else:

                result_year = data["year"]
                result_quarter = data["quarter"]
                spending = data["spending"]

                answer = (
                    f"The highest-spending quarter "
                    f"was Q{result_quarter} {result_year}, "
                    f"with total recorded spending of "
                    f"${spending:,.2f}."
                )

        # MOST FREQUENTLY ORDERED ITEMS
        elif intent == "most_frequent_items":

            if not data:

                answer = (
                    "No matching items were found."
                )

            else:

                lines = [
                    f"Most frequently ordered items "
                    f"{context_text} "
                    f"(by line-item record count):"
                ]

                for index, row in enumerate(
                    data, start=1
                ):

                    lines.append(
                        f"{index}. {row['name']} — "
                        f"{row['frequency']:,} records"
                    )

                answer = "\n".join(lines)

        # YEARLY SPENDING
        elif intent == "yearly_spending":

            if not data:

                answer = (
                    "No matching records were found."
                )

            else:

                lines = [
                    f"Spending by calendar year "
                    f"{context_text}:"
                ]

                for row in data:

                    lines.append(
                        f"{row['year']}: "
                        f"${row['spending']:,.2f}"
                    )

                answer = "\n".join(lines)

        # TOP SUPPLIERS / DEPARTMENTS / ITEMS
        elif intent in (
            "top_suppliers",
            "top_departments",
            "top_items"
        ):

            if not data:

                answer = (
                    "No matching records were found."
                )

            else:

                titles = {
                    "top_suppliers": "Top suppliers",
                    "top_departments": "Top departments",
                    "top_items": "Top items by spending"
                }

                lines = [
                    f"{titles[intent]} {context_text}:"
                ]

                for index, row in enumerate(
                    data, start=1
                ):

                    lines.append(
                        f"{index}. {row['name']} — "
                        f"${row['spending']:,.2f}"
                    )

                answer = "\n".join(lines)

        # OTHER SUPPORTED ANALYSES
        else:

            answer = (
                "The database query completed successfully."
            )

        # --------------------------------------
        # STEP 7: RETURN RESPONSE TO REACT
        # --------------------------------------

        return {
    "question": question,
    "intent": intent,
    "plan": plan,
    "data": data,
    "answer": answer,
    "insights": generate_insights(
        intent=intent,
        data=data,
        plan=plan
    )
}

    # --------------------------------------
    # HANDLE INVALID OR UNSUPPORTED FILTERS
    # --------------------------------------

    except ValueError as error:

        logger.warning(
            "Unsupported query: %s",
            error
        )

        return {
            "question": question,
            "intent": "UNSUPPORTED",
            "data": None,
            "answer": (
                "I couldn't process that question "
                "with the currently supported filters. "
                "Please check the requested year, "
                "month, quarter, or analysis type."
            )
        }

    # --------------------------------------
    # HANDLE UNEXPECTED ERRORS
    # --------------------------------------

    except Exception as error:

        logger.exception("CHAT ERROR")

        raise HTTPException(
            status_code=500,
            detail="Unable to process the question"
        ) from error


@app.get("/app")
def chatbot_page():
    return FileResponse("static/index.html")



# ==========================================
# DASHBOARD ANALYTICS ENDPOINT
# ==========================================

@app.get("/dashboard")
def dashboard():
    try:
        return {
            "summary": {
                "total_records": collection.count_documents({}),
                "total_spending": total_spending(),
                "currency": "USD"
            },
            "yearly_spending": spending_by_year(),
            "top_suppliers": top_group("Supplier Name", 5),
            "top_departments": top_group("Department Name", 5)
        }

    except Exception as error:
        logger.exception("Dashboard error")
        raise HTTPException(
            status_code=500,
            detail="Unable to load dashboard data"
        ) from error

