
import csv
import time
from pathlib import Path

from backend.query_engine import (
    understand_question,
    validate_plan,
)
from backend.query_executor import execute_plan


# ==========================================
# EVALUATION TEST CASES
# ==========================================

TEST_CASES = [
    # Previously passing tests
    {
        "question": "How much was spent in Q2 2013?",
        "analysis": "total_spending",
        "expected": 19013469394.04,
        "key": "total_spending",
        "filters": {"year": 2013, "quarter": 2},
    },
    {
        "question": "How many purchase orders were created in March 2014?",
        "analysis": "unique_order_count",
        "expected": 5672,
        "key": "unique_order_count",
        "filters": {"year": 2014, "month": 3},
    },
    {
        "question": "How many purchase orders are in the entire dataset?",
        "analysis": "unique_order_count",
        "expected": 200526,
        "key": "unique_order_count",
        "filters": {"year": None, "month": None, "quarter": None},
    },
    {
        "question": "How much was spent in 2016?",
        "analysis": "unsupported",
    },
    {
        "question": "Compare spending between 2013 and 2014",
        "analysis": "unsupported",
    },
    {
        "question": "How many orders were created in Q2?",
        "analysis": "unsupported",
    },

    # Additional spending and filtering tests
    {
        "question": "What was the spending in March 2014?",
        "analysis": "total_spending",
        "expected": 5293888708.42,
        "key": "total_spending",
        "filters": {"year": 2014, "month": 3},
    },
    {
        "question": "How much did the Department of Public Health spend in 2013?",
        "analysis": "total_spending",
        "expected": 3450189697.79,
        "key": "total_spending",
        "filters": {
            "year": 2013,
            "department": "Public Health, Department of",
        },
    },

    # Ranking tests
    {
        "question": "Which department spent the most in 2014?",
        "analysis": "top_departments",
        "limit": 1,
        "filters": {"year": 2014},
        "result_type": "ranking",
    },
    {
        "question": "What were the top 5 suppliers in March 2014?",
        "analysis": "top_suppliers",
        "limit": 5,
        "filters": {"year": 2014, "month": 3},
        "result_type": "ranking",
    },
    {
        "question": "What were the top 5 items by spending in 2015?",
        "analysis": "top_items",
        "limit": 5,
        "filters": {"year": 2015},
        "result_type": "ranking",
    },
    {
        "question": "What were the top 5 most frequently purchased items in 2015?",
        "analysis": "most_frequent_items",
        "limit": 5,
        "filters": {"year": 2015},
        "result_type": "frequency",
        "expected_first_name": "Medical Vocational Training Services",
        "expected_first_frequency": 508,
    },

    # Highest-spending quarter
    {
        "question": "Which quarter had the highest spending in 2013?",
        "analysis": "highest_spending_quarter",
        "filters": {"year": 2013},
        "result_type": "quarter",
        "expected_year": 2013,
        "expected_quarter": 1,
        "expected_spending": 25788088561.68,
    },

    # Additional order and unsupported tests
    {
        "question": "How many orders did the Department of Public Health create in Q2 2013?",
        "analysis": "unique_order_count",
        "expected": 405,
        "key": "unique_order_count",
        "filters": {
            "year": 2013,
            "quarter": 2,
            "department": "Public Health, Department of",
        },
    },
    {
        "question": "How much was spent in 2020?",
        "analysis": "unsupported",
    },

    # Validation-only tests
    {
        "question": "Reject invalid month 13",
        "result_type": "validation",
        "plan": {
            "analysis": "total_spending",
            "year": 2014,
            "month": 13,
        },
    },
    {
        "question": "Reject unsupported database operation",
        "result_type": "validation",
        "plan": {
            "analysis": "delete_collection",
        },
    },
    {
        "question": "Reject excessive result limit",
        "result_type": "validation",
        "plan": {
            "analysis": "top_suppliers",
            "year": 2014,
            "limit": 100,
        },
    },
]


# ==========================================
# HELPERS
# ==========================================

def numbers_match(actual, expected, tolerance=0.05):
    return (
        isinstance(actual, (int, float))
        and not isinstance(actual, bool)
        and abs(actual - expected) <= tolerance
    )


def check_filters(plan, expected_filters):
    for key, expected_value in expected_filters.items():
        if plan.get(key) != expected_value:
            return False, (
                f"Filter {key}: expected {expected_value}, "
                f"got {plan.get(key)}"
            )

    return True, ""


def check_ranking(data, expected_limit, frequency=False):
    if not isinstance(data, list):
        return False, "Expected a list"

    if not 1 <= len(data) <= expected_limit:
        return False, "Unexpected number of ranking results"

    metric = "frequency" if frequency else "spending"

    for row in data:
        if not isinstance(row, dict):
            return False, "Invalid ranking row"

        if "name" not in row or metric not in row:
            return False, f"Missing name or {metric}"

        if not isinstance(row[metric], (int, float)):
            return False, f"Invalid {metric} value"

    values = [row[metric] for row in data]

    if values != sorted(values, reverse=True):
        return False, "Ranking is not sorted descending"

    return True, ""


# ==========================================
# EVALUATION
# ==========================================

def run_test(case):
    start = time.perf_counter()

    actual_value = None
    error = ""
    source = ""
    passed = False

    try:
        # Validation tests intentionally supply
        # invalid plans and expect rejection.
        if case.get("result_type") == "validation":
            try:
                validate_plan(case["plan"])
                error = "Invalid plan was incorrectly accepted"
            except ValueError:
                passed = True

        else:
            plan = understand_question(case["question"])
            source = plan.get("source", "")

            if plan["analysis"] != case["analysis"]:
                error = (
                    f"Expected analysis {case['analysis']}, "
                    f"got {plan['analysis']}"
                )

            else:
                filters_ok, filter_error = check_filters(
                    plan,
                    case.get("filters", {}),
                )

                if not filters_ok:
                    error = filter_error

                elif (
                    "limit" in case
                    and plan.get("limit") != case["limit"]
                ):
                    error = (
                        f"Expected limit {case['limit']}, "
                        f"got {plan.get('limit')}"
                    )

                elif plan["analysis"] == "unsupported":
                    passed = True

                else:
                    data = execute_plan(plan)
                    result_type = case.get("result_type")

                    if result_type in ("ranking", "frequency"):
                        passed, error = check_ranking(
                            data,
                            case["limit"],
                            frequency=(result_type == "frequency"),
                        )

                        if passed and result_type == "frequency":
                            first = data[0]

                            if (
                                first["name"]
                                != case["expected_first_name"]
                                or first["frequency"]
                                != case["expected_first_frequency"]
                            ):
                                passed = False
                                error = "Unexpected top-frequency item"

                        actual_value = str(data[:2])

                    elif result_type == "quarter":
                        actual_value = str(data)

                        passed = (
                            isinstance(data, dict)
                            and data.get("year")
                            == case["expected_year"]
                            and data.get("quarter")
                            == case["expected_quarter"]
                            and numbers_match(
                                data.get("spending"),
                                case["expected_spending"],
                            )
                        )

                        if not passed:
                            error = "Highest-spending quarter mismatch"

                    else:
                        actual_value = (
                            data.get(case["key"])
                            if isinstance(data, dict)
                            else None
                        )

                        passed = numbers_match(
                            actual_value,
                            case["expected"],
                        )

                        if not passed:
                            error = (
                                f"Expected {case['expected']}, "
                                f"got {actual_value}"
                            )

    except Exception as exc:
        passed = False
        error = f"{type(exc).__name__}: {exc}"

    elapsed = round(time.perf_counter() - start, 3)

    return {
        "question": case["question"],
        "status": "PASS" if passed else "FAIL",
        "actual_value": actual_value,
        "source": source,
        "response_time_seconds": elapsed,
        "error": error,
    }


def main():
    results = []

    print("=" * 65)
    print("AI PROCUREMENT ASSISTANT - EXPANDED EVALUATION")
    print("=" * 65)

    for index, case in enumerate(TEST_CASES, 1):
        result = run_test(case)
        results.append(result)

        print(f"\nTest {index}: {result['status']}")
        print(f"Question: {result['question']}")
        print(
            f"Time: {result['response_time_seconds']} seconds"
        )

        if result["actual_value"] is not None:
            print(f"Actual: {result['actual_value']}")

        if result["error"]:
            print(f"Error: {result['error']}")

    # Save CSV report.
    output_dir = Path("evaluation_results")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "expanded_evaluation_report.csv"

    with output_file.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "question",
                "status",
                "actual_value",
                "source",
                "response_time_seconds",
                "error",
            ],
        )

        writer.writeheader()
        writer.writerows(results)

    passed = sum(
        row["status"] == "PASS"
        for row in results
    )

    failed = len(results) - passed

    print("\n" + "=" * 65)
    print(f"PASSED: {passed}/{len(results)}")
    print(f"FAILED: {failed}")
    print(f"PASS RATE: {passed / len(results) * 100:.1f}%")
    print(f"REPORT: {output_file}")
    print("=" * 65)


if __name__ == "__main__":
    main()
