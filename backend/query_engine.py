
import os
import re
import json
import time
import random

from dotenv import load_dotenv
from google import genai
from google.genai import errors

# ==========================================
# CONFIGURATION
# ==========================================

load_dotenv()

MODEL_NAME = "gemini-3.8-flash"

api_key = os.getenv("GEMINI_API_KEY")

client = (
    genai.Client(api_key=api_key)
    if api_key else None
)

ALLOWED_ANALYSES = [
    "total_spending",
    "record_count",
    "top_suppliers",
    "top_departments",
    "top_items",
    "yearly_spending",
    "unique_order_count",
    "highest_spending_quarter",
    "most_frequent_items"
]

# ==========================================
# MONTH AND QUARTER CONFIGURATION
# ==========================================

MONTH_NAMES = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12
}

QUARTER_NAMES = {
    "first quarter": 1,
    "second quarter": 2,
    "third quarter": 3,
    "fourth quarter": 4,
    "1st quarter": 1,
    "2nd quarter": 2,
    "3rd quarter": 3,
    "4th quarter": 4
}


# ==========================================
# LOCAL QUESTION UNDERSTANDING
# ==========================================

def local_parser(question):

    if not isinstance(question, str):
        return None

    q = question.lower().strip()

    if not q:
        return None

    # --------------------------------------
    # EXTRACT CALENDAR YEAR
    # --------------------------------------

    years = re.findall(
        r"\b20(?:12|13|14|15)\b",
        q
    )

    if len(set(years)) > 1:
        return None

    year = int(years[0]) if years else None

    # Reject unsupported years rather than
    # accidentally ignoring them.
    all_years = re.findall(r"\b20\d{2}\b", q)

    if any(
        int(value) not in range(2012, 2016)
        for value in all_years
    ):
        return None

    # --------------------------------------
    # EXTRACT MONTH
    # --------------------------------------

    found_months = [
        number
        for name, number in MONTH_NAMES.items()
        if re.search(rf"\b{name}\b", q)
    ]

    if len(found_months) > 1:
        return None

    month = (
        found_months[0]
        if found_months
        else None
    )

    # --------------------------------------
    # EXTRACT QUARTER
    # --------------------------------------

    found_quarters = []

    quarter_matches = re.findall(
        r"\bq([1-4])\b",
        q
    )

    found_quarters.extend(
        int(value)
        for value in quarter_matches
    )

    for name, number in QUARTER_NAMES.items():
        if re.search(rf"\b{re.escape(name)}\b", q):
            found_quarters.append(number)

    if len(set(found_quarters)) > 1:
        return None

    quarter = (
        found_quarters[0]
        if found_quarters
        else None
    )

    # Reject invalid quarter labels.
    if re.search(r"\bq\d+\b", q) and not quarter_matches:
        return None

    # A month or quarter requires a year.
    if (
        month is not None
        or quarter is not None
    ) and year is None:
        return None

    # Month and quarter cannot be combined.
    if month is not None and quarter is not None:
        return None

    # --------------------------------------
    # EXTRACT TOP N
    # --------------------------------------

    top_match = re.search(
        r"\btop\s+(\d+)\b",
        q
    )

    number_match = re.search(
        r"\b(?:top|highest|largest)\s+(\d+)\b",
        q
    )

    explicit_limit = (
        top_match or number_match
    )

    if explicit_limit:
        limit = min(
            max(int(explicit_limit.group(1)), 1),
            20
        )
    else:
        limit = 5

    # --------------------------------------
    # EXTRACT COMMON DEPARTMENT NAME
    # --------------------------------------

    department = None

    department_aliases = {
        "department of public health":
            "Public Health, Department of",

        "public health, department of":
            "Public Health, Department of",

        "department of health care services":
            "Health Care Services, Department of",

        "health care services, department of":
            "Health Care Services, Department of",

        "department of social services":
            "Social Services, Department of",

        "social services, department of":
            "Social Services, Department of"
    }

    for alias, official_name in department_aliases.items():

        if alias in q:
            department = official_name
            break

    # --------------------------------------
    # REJECT UNSUPPORTED FILTERS
    # --------------------------------------

    unsupported_terms = [
        "compare",
        "versus",
        "between",
        "fiscal year",
        "acquisition method"
    ]

    if any(
        term in q
        for term in unsupported_terms
    ):
        return None

    # --------------------------------------
    # DETECT QUESTION INTENT
    # --------------------------------------

    asks_count = bool(
        re.search(
            r"\b(?:how many|count|number of|"
            r"total number)\b",
            q
        )
    )

    mentions_orders = bool(
        re.search(
            r"\b(?:purchase\s+orders?|"
            r"unique\s+orders?|"
            r"distinct\s+orders?|"
            r"orders?)\b",
            q
        )
    )

    mentions_items = bool(
        re.search(
            r"\b(?:items?|products?)\b",
            q
        )
    )

    mentions_suppliers = bool(
        re.search(
            r"\b(?:suppliers?|vendors?)\b",
            q
        )
    )

    mentions_departments = bool(
        re.search(
            r"\bdepartments?\b",
            q
        )
    )

    asks_frequency = bool(
        re.search(
            r"\b(?:frequent|frequently|frequency|"
            r"most ordered|most purchased|"
            r"commonly ordered|commonly purchased)\b",
            q
        )
    )

    asks_spending = bool(
        re.search(
            r"\b(?:spend|spent|spending|"
            r"expenditure|expenditures)\b",
            q
        )
    )

    asks_yearly = bool(
        re.search(
            r"\b(?:yearly|annual|annually|"
            r"by year|trend)\b",
            q
        )
    )

    asks_highest = bool(
        re.search(
            r"\b(?:highest|largest|maximum|"
            r"most spending|most spent)\b",
            q
        )
    )

    # --------------------------------------
    # IDENTIFY REQUESTED ANALYSIS
    # --------------------------------------

    # P1.3: Highest-spending quarter.
    if (
        re.search(r"\bquarter\b", q)
        and asks_highest
        and asks_spending
    ):
        analysis = "highest_spending_quarter"

    # P1.3: Most frequently ordered items.
    elif mentions_items and asks_frequency:
        analysis = "most_frequent_items"

    # P1.3: Unique purchase-order count.
    elif mentions_orders and asks_count:
        analysis = "unique_order_count"

    # Existing: Supplier ranking.
    elif mentions_suppliers:
        analysis = "top_suppliers"

    # Existing: Department ranking.
    elif mentions_departments and department is None:
        analysis = "top_departments"

    # Existing: Item ranking by spending.
    elif mentions_items:
        analysis = "top_items"

    # Existing: Yearly spending.
    elif asks_yearly:
        analysis = "yearly_spending"

    # Existing: Line-item record count.
    elif asks_count and not mentions_orders:
        analysis = "record_count"

    # Existing: Total spending.
    elif asks_spending:
        analysis = "total_spending"

    else:
        return None

    # --------------------------------------
    # AVOID MISLEADING LOCAL INTERPRETATIONS
    # --------------------------------------

    # Counting orders is not the same as
    # counting procurement line-item records.
    if mentions_orders and analysis == "record_count":
        return None

    # A known department in a spending question
    # should be used as a filter.
    if (
        department is not None
        and asks_spending
        and not mentions_items
        and not mentions_suppliers
        and not asks_yearly
        and analysis not in (
            "highest_spending_quarter",
            "unique_order_count"
        )
    ):
        analysis = "total_spending"

    # --------------------------------------
    # SINGULAR RANKING REQUESTS
    # --------------------------------------

    # Only set limit=1 for explicit singular
    # ranking requests, not frequency questions.
    singular_ranking = bool(
        re.search(
            r"\b(?:which|what|who)\s+"
            r"(?:supplier|vendor|department|item|product)\b",
            q
        )
        and re.search(
            r"\b(?:the most|the highest|the largest)\b",
            q
        )
    )

    if (
        explicit_limit is None
        and singular_ranking
        and analysis in (
            "top_suppliers",
            "top_departments",
            "top_items"
        )
    ):
        limit = 1

    # --------------------------------------
    # RETURN QUERY PLAN
    # --------------------------------------

    return {
        "analysis": analysis,
        "year": year,
        "month": month,
        "quarter": quarter,
        "supplier": None,
        "department": department,
        "limit": limit,
        "source": "local_parser"
    }


# ==========================================
# VALIDATE QUERY PLAN
# ==========================================

def validate_plan(plan):

    if not isinstance(plan, dict):
        raise ValueError("Invalid query plan")

    analysis = plan.get("analysis")

    # --------------------------------------
    # UNSUPPORTED PLAN
    # --------------------------------------

    if analysis == "unsupported":
        return {
            "analysis": "unsupported",
            "year": None,
            "month": None,
            "quarter": None,
            "supplier": None,
            "department": None,
            "limit": 5,
            "source": plan.get("source", "gemini")
        }

    if analysis not in ALLOWED_ANALYSES:
        raise ValueError("Unsupported analysis")

    # --------------------------------------
    # VALIDATE YEAR
    # --------------------------------------

    year = plan.get("year")

    if year is not None:
        if (
            type(year) is not int
            or not 2012 <= year <= 2015
        ):
            raise ValueError("Invalid calendar year")

    # --------------------------------------
    # VALIDATE MONTH
    # --------------------------------------

    month = plan.get("month")

    if month is not None:
        if (
            type(month) is not int
            or not 1 <= month <= 12
        ):
            raise ValueError("Invalid month")

    # --------------------------------------
    # VALIDATE QUARTER
    # --------------------------------------

    quarter = plan.get("quarter")

    if quarter is not None:
        if (
            type(quarter) is not int
            or not 1 <= quarter <= 4
        ):
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
            "Month or quarter requires a calendar year"
        )

    # --------------------------------------
    # VALIDATE LIMIT
    # --------------------------------------

    limit = plan.get("limit", 5)

    if (
        type(limit) is not int
        or not 1 <= limit <= 20
    ):
        raise ValueError("Invalid result limit")

    # --------------------------------------
    # VALIDATE SUPPLIER AND DEPARTMENT
    # --------------------------------------

    for field in ("supplier", "department"):

        value = plan.get(field)

        if value is not None:

            if not isinstance(value, str):
                raise ValueError("Invalid filter")

            if (
                not value.strip()
                or len(value) > 150
            ):
                raise ValueError("Invalid filter")

    # --------------------------------------
    # VALIDATE ANALYSIS-SPECIFIC FILTERS
    # --------------------------------------

    if analysis == "highest_spending_quarter":

        if month is not None or quarter is not None:
            raise ValueError(
                "Highest-spending-quarter analysis "
                "cannot use a month or quarter filter"
            )

    # --------------------------------------
    # RETURN VALIDATED PLAN
    # --------------------------------------

    return {
        "analysis": analysis,
        "year": year,
        "month": month,
        "quarter": quarter,
        "supplier": plan.get("supplier"),
        "department": plan.get("department"),
        "limit": limit,
        "source": plan.get("source", "gemini")
    }


# ==========================================
# GEMINI QUESTION UNDERSTANDING
# ==========================================

def gemini_parser(question):

    if client is None:
        raise RuntimeError(
            "Gemini API key is not configured"
        )

    prompt = f"""
You are a procurement query planner.

Convert the user question into a JSON query plan.

Allowed analyses:
{json.dumps(ALLOWED_ANALYSES)}

Return exactly this JSON structure:

{{
    "analysis": "total_spending",
    "year": null,
    "month": null,
    "quarter": null,
    "supplier": null,
    "department": null,
    "limit": 5
}}

Rules:
- Use only allowed analyses.
- Year must be 2012, 2013, 2014, or 2015.
- Month must be between 1 and 12, or null.
- Quarter must be between 1 and 4, or null.
- A month or quarter requires a year.
- Month and quarter cannot both be set.
- Limit must be between 1 and 20.
- Use null when a filter is absent.
- Do not invent supplier or department names.
- Do not generate MongoDB commands.
- If unsupported, set analysis to "unsupported".
- Return JSON only.

Analysis definitions:
- total_spending:
  Sum procurement spending.

- record_count:
  Count procurement line-item records.

- unique_order_count:
  Count distinct Purchase Order Number values.

- top_suppliers:
  Rank suppliers by total spending.

- top_departments:
  Rank departments by total spending.

- top_items:
  Rank item names by total spending.

- yearly_spending:
  Group spending by calendar year.

- highest_spending_quarter:
  Find the calendar quarter with the highest
  total spending.

- most_frequent_items:
  Rank item names by line-item record frequency.

Important distinctions:
- "How many orders" means unique_order_count.
- "How many records" means record_count.
- "Most frequently ordered items" means
  most_frequent_items.
- "Top items by spending" means top_items.
- "Which department spent the most" means
  top_departments with limit 1.
- If a question asks for a comparison between
  two years, return unsupported.

Examples:

Question:
How many orders did the Department of Public Health
create in Q2 2013?

Analysis:
unique_order_count

Question:
Which department spent the most in 2014?

Analysis:
top_departments

Limit:
1

Question:
What were the top 10 most frequently ordered
items in 2015?

Analysis:
most_frequent_items

Limit:
10

Question:
{question}
"""

    # --------------------------------------
    # CALL GEMINI WITH RETRIES
    # --------------------------------------

    for attempt in range(3):

        try:

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )

            text = (response.text or "").strip()

            # Remove Markdown code fences.
            if text.startswith("```"):

                text = re.sub(
                    r"^```(?:json)?\s*",
                    "",
                    text
                )

                text = re.sub(
                    r"\s*```$",
                    "",
                    text
                )

                text = text.strip()

            plan = json.loads(text)

            if not isinstance(plan, dict):
                raise ValueError(
                    "Gemini returned an invalid query plan"
                )

            plan["source"] = "gemini"

            return validate_plan(plan)

        except errors.ServerError as error:

            if error.code not in (
                500, 502, 503, 504
            ):
                raise

            if attempt == 2:
                raise

            wait_time = (
                (2 ** attempt)
                + random.uniform(0, 1)
            )

            print(
                f"Gemini temporarily busy. "
                f"Retrying in {wait_time:.1f} seconds..."
            )

            time.sleep(wait_time)


# ==========================================
# FALLBACK PLAN
# ==========================================

def unsupported_plan():

    return {
        "analysis": "unsupported",
        "year": None,
        "month": None,
        "quarter": None,
        "supplier": None,
        "department": None,
        "limit": 5,
        "source": "fallback"
    }


# ==========================================
# MAIN FUNCTION
# ==========================================

def understand_question(question):


    # Reject unsupported calendar years.
    mentioned_years = re.findall(
        r"\b20\d{2}\b",
        question
    )

    if any(
        int(y) not in (2012, 2013, 2014, 2015)
        for y in mentioned_years
    ):
        return unsupported_plan()

    # Comparisons between multiple years are
    # not supported by the current executor.
    if len(set(mentioned_years)) > 1:
        return unsupported_plan()

    # Reject unsupported comparison requests.
    if re.search(
        r"\b(compare|versus|between)\b",
        question.lower()
    ):
        return unsupported_plan()

    # Do not let Gemini invent a year for
    # a month or quarter question.
    has_period = (
        re.search(r"\bq[1-4]\b", question.lower())
        or re.search(
            r"\b(?:first|second|third|fourth)\s+quarter\b",
            question.lower()
        )
        or any(
            re.search(rf"\b{name}\b", question.lower())
            for name in MONTH_NAMES
        )
    )

    if has_period and not mentioned_years:
        return unsupported_plan()


    # --------------------------------------
    # STEP 1: LOCAL PARSER
    # --------------------------------------

    local_result = local_parser(question)

    if local_result is not None:
        return validate_plan(local_result)

    # --------------------------------------
    # STEP 2: GEMINI FALLBACK
    # --------------------------------------

    try:
        return gemini_parser(question)

    except errors.ClientError as error:

        if error.code == 429:

            print(
                "Gemini daily quota exhausted. "
                "Local parsing remains available."
            )

            return unsupported_plan()

        raise

    except errors.ServerError:

        print("Gemini unavailable.")

        return unsupported_plan()

    except RuntimeError as error:

        print(
            f"Gemini configuration issue: {error}"
        )

        return unsupported_plan()

    except (
        ValueError,
        json.JSONDecodeError
    ) as error:

        print(
            f"Gemini returned an invalid plan: {error}"
        )

        return unsupported_plan()
