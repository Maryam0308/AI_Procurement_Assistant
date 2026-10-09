
from query_engine import understand_question
from query_executor import execute_plan

questions = [
    "Who were the top 5 suppliers in 2014?",
    "How much did the Department of Public Health spend in 2013?",
    "Show the top 10 items purchased in 2015."
]

for question in questions:

    print("\nQUESTION:", question)

    try:
        plan = understand_question(question)

        print("QUERY PLAN:", plan)

        result = execute_plan(plan)

        print("DATABASE RESULT:", result)

    except Exception as error:
        print("ERROR:", error)
