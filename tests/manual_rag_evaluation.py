
import time
import httpx

API_URL = "http://127.0.0.1:8000/support/ask"

questions = [
    "How much is express shipping?",
    "How much is express shipping, and when will it arrive?",
    "Do you offer lifetime warranties?",
    "Where is my order ORD-9999?",
    "My personalized item arrived damaged. Can I get a refund?",
    "Who won the 2022 FIFA World Cup?",
]

with httpx.Client(timeout=120.0) as client:
    for number, question in enumerate(questions, start=1):
        print(f"\n{'=' * 65}")
        print(f"TEST {number}: {question}")

        start = time.perf_counter()

        try:
            response = client.post(
                API_URL,
                json={"question": question},
            )
            response.raise_for_status()
            result = response.json()

            print(f"ANSWER: {result['answer']}")
            print(
                "SOURCES:",
                [source["id"] for source in result["sources"]],
            )

        except (httpx.HTTPError, ValueError, KeyError) as exc:
            print(f"ERROR: {exc}")

        elapsed = time.perf_counter() - start
        print(f"LATENCY: {elapsed:.2f}s")