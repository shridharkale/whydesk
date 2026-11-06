"""Verification script for Task 3: Runs 1 to 5 memory ON, then Run 5 memory OFF."""

import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.agent import WhyDeskAgent
from backend.memory import WhyDeskMemory


def main():
    memory = WhyDeskMemory()
    print(f"Active Backend: {memory.backend_type}")
    print("Resetting memory bank...")
    memory.reset_bank()

    agent = WhyDeskAgent(memory=memory)

    runs = [
        (
            1,
            "Finance Head",
            "Why did revenue drop 18% in the South region in W10, and FYI I only ever want a 1-line summary with the exact dollar impact.",
            True,
        ),
        (
            2,
            "Senior Analyst",
            "Alert says Monday revenue in W11 is down 64% across South. Did pricing break again?",
            True,
        ),
        (
            3,
            "Senior Analyst",
            "North hardware bundle revenue dipped 24% in W11. Sales blames a competitor promo or holiday. True?",
            True,
        ),
        (
            4,
            "Senior Analyst",
            "South region revenue dropped 15% again in W12. Investigate.",
            True,
        ),
        (
            5,
            "Finance Head",
            "Why did revenue drop 19% in the South region in W13?",
            True,
        ),
        (
            "5 (Memory OFF)",
            "Finance Head",
            "Why did revenue drop 19% in the South region in W13?",
            False,
        ),
    ]

    results = []
    for run_num, stakeholder, question, use_memory in runs:
        print(f"\nExecuting Run {run_num} (use_memory={use_memory})...")
        res = agent.investigate(
            question=question,
            stakeholder=stakeholder,
            use_memory=use_memory,
        )
        tool_names = [t["tool"] for t in res["tool_trace"]]
        results.append({
            "run": run_num,
            "stakeholder": stakeholder,
            "tool_order": tool_names,
            "tool_count": len(tool_names),
            "recalled_count": len(res.get("recall_results", [])),
            "answer": res["answer"],
        })

    print("\n" + "=" * 100)
    print("TASK 3 VERIFICATION TABLE")
    print("=" * 100)
    for r in results:
        print(f"Run: {r['run']}")
        print(f"Tools in Order ({r['tool_count']}): {', '.join(r['tool_order'])}")
        print(f"Recalled Memories Count: {r['recalled_count']}")
        print(f"Answer: {r['answer']}")
        print("-" * 100)


if __name__ == "__main__":
    main()
