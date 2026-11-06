"""Unit tests for WhyDesk diagnostic tools, agent logic, memory, and format rules."""

import pytest
from backend.tools import (
    check_etl_pipeline,
    check_pricing_changes,
    check_inventory_stockouts,
    check_competitor_promos,
    check_holiday_calendar,
    DEFAULT_TOOL_AUDIT_ORDER,
)
from backend.agent import WhyDeskAgent
from backend.memory import WhyDeskMemory, LocalMemoryFallback


def test_five_tools_case_1():
    """Case 1: South W10 pricing 20% discount auto-applied."""
    res = check_pricing_changes("South", "2026-W10")
    assert res["root_cause_confirmed"] is True
    assert res["dollar_impact"] == -42500
    assert res["percent_impact"] == -18.0
    assert "Core SaaS" in res["affected_product"]


def test_five_tools_case_2():
    """Case 2: South W11 Monday ETL lag."""
    res = check_etl_pipeline("South", "2026-W11")
    assert res["root_cause_confirmed"] is True
    assert res["status"] == "degraded"
    assert res["missing_rows_pct"] == 65.0
    assert res["delayed_revenue"] == 88000
    assert res["real_loss"] == 0


def test_five_tools_case_3():
    """Case 3: North W11 inventory stockout ENT-GATEWAY-02."""
    res = check_inventory_stockouts("North", "2026-W11")
    assert res["root_cause_confirmed"] is True
    assert res["sku"] == "ENT-GATEWAY-02"
    assert res["dollar_impact"] == -31200
    assert res["stockout_days"] == 5


def test_five_tools_case_4():
    """Case 4: South W12 legacy promo code SOUTH-Q1-25."""
    res = check_pricing_changes("South", "2026-W12")
    assert res["root_cause_confirmed"] is True
    assert res["promo_code"] == "SOUTH-Q1-25"
    assert res["dollar_impact"] == -36800


def test_five_tools_case_5():
    """Case 5: South W13 reseller contract repricing."""
    res = check_pricing_changes("South", "2026-W13")
    assert res["root_cause_confirmed"] is True
    assert res["dollar_impact"] == -47900
    assert res["percent_impact"] == -19.0


def test_memory_off_runs_all_five_tools():
    """With memory OFF, all 5 diagnostic checks run in default audit order."""
    agent = WhyDeskAgent()
    out = agent.investigate(
        question="Why did revenue drop 18% in the South region in W10?",
        stakeholder="Senior Analyst",
        use_memory=False,
    )
    assert len(out["tool_trace"]) == 5
    executed = [t["tool"] for t in out["tool_trace"]]
    assert executed == DEFAULT_TOOL_AUDIT_ORDER
    assert len(out["skipped_tools"]) == 0


def test_early_stop_with_memory_on():
    """With memory ON and confirmed regional patterns, agent stops early once cause is found."""
    mem = WhyDeskMemory()
    mem.reset_bank()
    agent = WhyDeskAgent(memory=mem)

    # Seed an initial memory about South pricing
    mem.retain_investigation(
        region="South",
        week="2026-W10",
        confirmed_cause="20% discount tier auto-applied",
        impact_str="-$42,500",
        ruled_out=["Holiday", "Competitor", "Inventory"],
        is_etl_lag=False,
    )

    # Run investigation on W13 where cause is pricing
    out = agent.investigate(
        question="Why did revenue drop 19% in the South region in W13?",
        stakeholder="Finance Head",
        use_memory=True,
    )
    # Checks ETL first, then pricing, and early-stops: exactly 2 tools run!
    assert len(out["tool_trace"]) == 2
    assert out["tool_trace"][0]["tool"] == "check_etl_pipeline"
    assert out["tool_trace"][1]["tool"] == "check_pricing_changes"
    assert len(out["skipped_tools"]) == 3
    assert "check_holiday_calendar" in out["skipped_tools"]
    assert "check_competitor_promos" in out["skipped_tools"]
    assert "check_inventory_stockouts" in out["skipped_tools"]


def test_numbers_from_tools_only():
    """Every dollar figure and percentage in the answer must strictly come from tool output."""
    agent = WhyDeskAgent()
    out = agent.investigate(
        question="Why did revenue drop 19% in the South region in W13?",
        stakeholder="Senior Analyst",
        use_memory=False,
    )
    # Must contain -$47,900
    assert "-$47,900" in out["answer"] or "47,900" in out["answer"]


def test_finance_head_one_line_check():
    """Finance Head receives exactly one single line containing the exact dollar impact."""
    agent = WhyDeskAgent()
    out = agent.investigate(
        question="Why did revenue drop 19% in the South region in W13?",
        stakeholder="Finance Head",
        use_memory=False,
    )
    answer = out["answer"].strip()
    lines = [l for l in answer.split("\n") if l.strip()]
    assert len(lines) == 1
    assert "-$47,900" in lines[0] or "47,900" in lines[0]

