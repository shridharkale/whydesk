"""Replays Runs 1 to 4 through the real pipeline on a fresh bank."""

import sys
from pathlib import Path

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.agent import WhyDeskAgent
from backend.memory import WhyDeskMemory


def seed_demo_history():
    print("==================================================")
    print("WhyDesk: Seeding Demo History (Runs 1 to 4)")
    print("==================================================")

    memory = WhyDeskMemory()
    print(f"Active Backend: {memory.backend_type} (Bank: {memory.bank_id})")
    print("Resetting memory bank to clean state...")
    memory.reset_bank()

    agent = WhyDeskAgent(memory=memory)

    demo_runs = [
        {
            "run": 1,
            "title": "Cold start (Finance Head)",
            "stakeholder": "Finance Head",
            "question": "Why did revenue drop 18% in the South region in W10, and FYI I only ever want a 1-line summary with the exact dollar impact.",
        },
        {
            "run": 2,
            "title": "Unreliable data source (Senior Analyst)",
            "stakeholder": "Senior Analyst",
            "question": "Alert says Monday revenue in W11 is down 64% across South. Did pricing break again?",
        },
        {
            "run": 3,
            "title": "Ruled-out hypotheses (Senior Analyst)",
            "stakeholder": "Senior Analyst",
            "question": "North hardware bundle revenue dipped 24% in W11. Sales blames a competitor promo or holiday. True?",
        },
        {
            "run": 4,
            "title": "Pattern consolidation (Senior Analyst)",
            "stakeholder": "Senior Analyst",
            "question": "South region revenue dropped 15% again in W12. Investigate.",
        },
    ]

    for item in demo_runs:
        run_num = item["run"]
        print(f"\n[Run {run_num}] {item['title']}")
        print(f"Stakeholder: {item['stakeholder']}")
        print(f"Question: \"{item['question']}\"")

        res = agent.investigate(
            question=item["question"],
            stakeholder=item["stakeholder"],
            use_memory=True,
        )

        trace = res["tool_trace"]
        skipped = res["skipped_tools"]
        print(f"  Tools run: {len(trace)} ({', '.join([t['tool'] for t in trace])})")
        if skipped:
            print(f"  Skipped: {len(skipped)} ({', '.join(skipped)})")
        print(f"  Answer: {res['answer']}")
        print(f"  Retained memories: {len(res['retained_payloads'])}")

    total_mems = len(memory.list_memories())
    print(f"\nSeeding complete. Memory bank now contains {total_mems} institutional memories.")
    print("Bank is primed for Run 5 climax.")


if __name__ == "__main__":
    seed_demo_history()

