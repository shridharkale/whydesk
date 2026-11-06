"""Smoke test script for WhyDesk: verifies all 5 cases with memory OFF."""

import sys
from pathlib import Path

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.agent import WhyDeskAgent
from backend.seed_data import CASES

CASES_TO_TEST = [
    {
        "case_num": 1,
        "question": "Why did revenue drop 18% in the South region in W10?",
        "expected_tool": "check_pricing_changes",
        "expected_impact": -42500,
        "expected_finding": "20% discount tier",
    },
    {
        "case_num": 2,
        "question": "Alert says Monday revenue in W11 is down 64% across South. Did pricing break again?",
        "expected_tool": "check_etl_pipeline",
        "expected_impact": 0,
        "expected_delayed": 88000,
        "expected_finding": "etl_sales_sync",
    },
    {
        "case_num": 3,
        "question": "North hardware bundle revenue dipped 24% in W11. Sales blames a competitor promo or holiday. True?",
        "expected_tool": "check_inventory_stockouts",
        "expected_impact": -31200,
        "expected_finding": "ENT-GATEWAY-02",
    },
    {
        "case_num": 4,
        "question": "South region revenue dropped 15% again in W12. Investigate.",
        "expected_tool": "check_pricing_changes",
        "expected_impact": -36800,
        "expected_finding": "SOUTH-Q1-25",
    },
    {
        "case_num": 5,
        "question": "Why did revenue drop 19% in the South region in W13?",
        "expected_tool": "check_pricing_changes",
        "expected_impact": -47900,
        "expected_finding": "reseller contract repricing",
    },
]


def run_smoke_tests():
    print("==================================================")
    print("Running WhyDesk Smoke Tests (Memory OFF, 5 Cases)")
    print("==================================================")
    agent = WhyDeskAgent()
    failures = 0

    for item in CASES_TO_TEST:
        c_num = item["case_num"]
        q = item["question"]
        print(f"\n[Case {c_num}] Question: {q}")

        result = agent.investigate(question=q, stakeholder="Senior Analyst", use_memory=False)

        # 1. Check tool execution count: with memory OFF, ALL 5 tools must execute
        trace = result["tool_trace"]
        if len(trace) != 5:
            print(f"  FAILED: Expected 5 tools to run with memory OFF, got {len(trace)}")
            failures += 1
            continue

        # 2. Check the confirming tool
        confirming_hits = [t for t in trace if t.get("root_cause_confirmed")]
        if not confirming_hits:
            print(f"  FAILED: No confirming tool identified in trace")
            failures += 1
            continue

        hit = confirming_hits[0]
        actual_tool = hit["tool"]
        raw = hit["raw_result"]

        if actual_tool != item["expected_tool"]:
            print(f"  FAILED: Expected confirming tool {item['expected_tool']}, got {actual_tool}")
            failures += 1
            continue

        # 3. Check dollar impact
        actual_impact = raw.get("dollar_impact", 0)
        if actual_impact != item["expected_impact"]:
            print(f"  FAILED: Expected impact {item['expected_impact']}, got {actual_impact}")
            failures += 1
            continue

        if "expected_delayed" in item:
            delayed = raw.get("delayed_revenue", 0)
            if delayed != item["expected_delayed"]:
                print(f"  FAILED: Expected delayed revenue {item['expected_delayed']}, got {delayed}")
                failures += 1
                continue

        # 4. Check findings text
        findings = hit["findings"].lower()
        if item["expected_finding"].lower() not in findings:
            print(f"  FAILED: Expected finding containing '{item['expected_finding']}', got '{hit['findings']}'")
            failures += 1
            continue

        # 5. Check answer string contains impact
        answer = result["answer"]
        if item["expected_impact"] < 0:
            impact_substr = f"{abs(item['expected_impact']):,}"
            if impact_substr not in answer:
                print(f"  FAILED: Answer does not contain impact {impact_substr}. Answer: {answer}")
                failures += 1
                continue

        print(f"  PASSED: Case {c_num} confirmed by {actual_tool} (Impact: ${actual_impact:,}). 5 of 5 tools ran.")

    print("\n--------------------------------------------------")
    if failures == 0:
        print("ALL 5 CASES PASSED SMOKE TEST SUCCESSFULLY.")
        return 0
    else:
        print(f"SMOKE TEST COMPLETED WITH {failures} FAILURE(S).")
        return 1


if __name__ == "__main__":
    sys.exit(run_smoke_tests())
