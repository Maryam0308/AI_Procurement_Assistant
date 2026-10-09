
"""
AI Procurement Assistant
P3.3 - Data-Driven Procurement Insights

Generates explanatory insights from verified MongoDB
query results without making additional AI API calls.
"""

from numbers import Real


def _number(value):
    """Convert a valid numeric value to float."""
    if isinstance(value, bool):
        return None

    if not isinstance(value, Real):
        return None

    result = float(value)

    if result != result or result in (
        float("inf"),
        float("-inf")
    ):
        return None

    return result


def _money(value):
    return f"${value:,.2f}"


def _percentage(value):
    return f"{value:.1f}%"


def generate_insights(intent, data, plan=None):
    """
    Return a list of factual, data-driven insights.

    Parameters
    ----------
    intent : str
        The validated analysis name.

    data : dict, list, or None
        Results returned by execute_plan().

    plan : dict or None
        Validated query plan.

    Returns
    -------
    list[str]
        Insight messages based only on query results.
    """

    plan = plan or {}
    insights = []

    if data is None:
        return insights

    # ======================================
    # TOTAL PROCUREMENT SPENDING
    # ======================================

    if intent == "total_spending":
        if not isinstance(data, dict):
            return insights

        spending = _number(data.get("total_spending"))

        if spending is None:
            return insights

        insights.append(
            "The recorded procurement spending "
            f"for the selected scope is {_money(spending)}."
        )

        insights.append(
            "This total represents procurement "
            "line-item spending, not the number "
            "of unique purchase orders."
        )

        return insights

    # ======================================
    # RECORD COUNT
    # ======================================

    if intent == "record_count":
        if not isinstance(data, dict):
            return insights

        count = _number(data.get("record_count"))

        if count is None:
            return insights

        insights.append(
            f"The selected scope contains {int(count):,} "
            "procurement line-item records."
        )

        insights.append(
            "Multiple line items may belong "
            "to the same purchase order."
        )

        return insights

    # ======================================
    # UNIQUE PURCHASE ORDER COUNT
    # ======================================

    if intent == "unique_order_count":
        if not isinstance(data, dict):
            return insights

        count = _number(data.get("unique_order_count"))

        if count is None:
            return insights

        insights.append(
            f"The selected scope includes {int(count):,} "
            "distinct nonblank purchase order numbers."
        )

        return insights

    # ======================================
    # HIGHEST-SPENDING QUARTER
    # ======================================

    if intent == "highest_spending_quarter":
        if not isinstance(data, dict):
            return insights

        spending = _number(data.get("spending"))
        year = data.get("year")
        quarter = data.get("quarter")

        if (
            spending is None
            or year is None
            or quarter is None
        ):
            return insights

        insights.append(
            f"Q{quarter} {year} had the highest "
            "recorded procurement spending "
            f"within the selected scope: {_money(spending)}."
        )

        insights.append(
            "This identifies the highest-spending "
            "quarter, but does not by itself explain "
            "which departments or suppliers drove "
            "the spending."
        )

        return insights

    # ======================================
    # RANKING ANALYSES
    # ======================================

    ranking_types = {
        "top_suppliers": "supplier",
        "top_departments": "department",
        "top_items": "item",
        "most_frequent_items": "item",
    }

    if intent in ranking_types:
        if not isinstance(data, list) or not data:
            return insights

        value_key = (
            "frequency"
            if intent == "most_frequent_items"
            else "spending"
        )

        rows = []

        for row in data:
            if not isinstance(row, dict):
                continue

            name = row.get("name")
            value = _number(row.get(value_key))

            if name is None or value is None:
                continue

            rows.append({
                "name": str(name),
                "value": value,
            })

        if not rows:
            return insights

        rows.sort(
            key=lambda row: row["value"],
            reverse=True
        )

        first = rows[0]
        category = ranking_types[intent]

        if value_key == "frequency":
            insights.append(
                f'The most frequently recorded {category} '
                f'is "{first["name"]}", appearing '
                f'{int(first["value"]):,} times '
                "as a procurement line item."
            )
        else:
            insights.append(
                f'The highest-ranked {category} is '
                f'"{first["name"]}", with recorded '
                f'spending of {_money(first["value"])}.'
            )

        # Compare the two leading results.
        if len(rows) >= 2:
            second = rows[1]

            if second["value"] > 0:
                difference = (
                    first["value"] - second["value"]
                )

                percentage = (
                    difference / second["value"]
                ) * 100

                if value_key == "frequency":
                    insights.append(
                        f'The leading item appears '
                        f'{int(difference):,} more times '
                        f'than "{second["name"]}" '
                        f'({_percentage(percentage)} more).'
                    )
                else:
                    insights.append(
                        f'The leading {category} exceeds '
                        f'the second-ranked {category} '
                        f'by {_money(difference)} '
                        f'({_percentage(percentage)} more).'
                    )

        # Calculate concentration within the
        # returned top-N results only.
        if value_key == "spending" and len(rows) >= 2:
            displayed_total = sum(
                row["value"] for row in rows
            )

            if displayed_total > 0:
                share = (
                    first["value"] / displayed_total
                ) * 100

                insights.append(
                    f'The leading {category} accounts for '
                    f'{_percentage(share)} of spending '
                    "among the displayed ranked results. "
                    "This is not a share of all "
                    "procurement spending."
                )

        if value_key == "frequency":
            insights.append(
                "Frequency measures line-item "
                "occurrences, not the quantity "
                "of units purchased."
            )

        return insights

    # ======================================
    # YEARLY SPENDING TRENDS
    # ======================================

    if intent == "yearly_spending":
        if not isinstance(data, list) or not data:
            return insights

        rows = []

        for row in data:
            if not isinstance(row, dict):
                continue

            year = row.get("year")
            spending = _number(row.get("spending"))

            if year is None or spending is None:
                continue

            rows.append({
                "year": year,
                "spending": spending,
            })

        if not rows:
            return insights

        rows.sort(key=lambda row: row["year"])

        highest = max(
            rows,
            key=lambda row: row["spending"]
        )

        insights.append(
            f'{highest["year"]} had the highest '
            "recorded spending among the returned "
            f'years, at {_money(highest["spending"])}.'
        )

        if len(rows) >= 2:
            first = rows[0]
            last = rows[-1]

            difference = (
                last["spending"] - first["spending"]
            )

            if first["spending"] != 0:
                change = (
                    difference / abs(first["spending"])
                ) * 100

                direction = (
                    "increased"
                    if difference > 0
                    else "decreased"
                    if difference < 0
                    else "remained unchanged"
                )

                insights.append(
                    f'Recorded spending {direction} '
                    f'by {_percentage(abs(change))} '
                    f'from {first["year"]} '
                    f'to {last["year"]}.'
                )

        insights.append(
            "These comparisons reflect the "
            "calendar-year records returned by "
            "the database query."
        )

        return insights

    return insights
