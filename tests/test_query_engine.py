
from query_engine import understand_question

questions = [
    "Who were the top 5 suppliers in 2014?",
    "How much did the Department of Public Health spend in 2013?",
    "Show the top 10 items purchased in 2015."
]

for question in questions:
    print("\nQUESTION:", question)

    try:
        result = understand_question(question)
        print("QUERY PLAN:", result)
    except Exception as error:
        print("ERROR:", error)
