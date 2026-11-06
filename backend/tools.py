"""Diagnostic tools for WhyDesk metric investigations."""

import time
from typing import Dict, Any, Tuple
from backend.seed_data import CASES, OTHER_SEEDED_EVENTS, normalize_region_and_week

DEFAULT_TOOL_AUDIT_ORDER = [
    "check_holiday_calendar",
    "check_competitor_promos",
    "check_inventory_stockouts",
    "check_pricing_changes",
    "check_etl_pipeline",
]


def check_etl_pipeline(region: str, week: str) -> Dict[str, Any]:
    """Check sync status, row counts, and latency logs for data ingestion pipelines."""
    norm_reg, norm_wk = normalize_region_and_week(region, week)
    case = CASES.get((norm_reg, norm_wk))

    if case and case.get("root_cause_tool") == "check_etl_pipeline":
        etl = case["etl"]
        return {
            "status": "degraded",
            "anomaly_detected": True,
            "root_cause_confirmed": True,
            "job_name": etl.get("job", "etl_sales_sync"),
            "stall_time_utc": etl.get("stall_time_utc", "02:00 UTC"),
            "missing_rows_pct": etl.get("missing_rows_pct", 65.0),
            "delayed_revenue": etl.get("delayed_revenue", 88000),
            "real_loss": etl.get("real_loss", 0),
            "dollar_impact": etl.get("dollar_impact", 0),
            "percent_impact": etl.get("percent_impact", -64.0),
            "findings": etl.get("findings"),
            "notes": etl.get("notes"),
        }
    elif case and "etl" in case:
        etl = case["etl"]
        return {
            "status": etl.get("status", "healthy"),
            "anomaly_detected": False,
            "root_cause_confirmed": False,
            "job_name": etl.get("job", "etl_sales_sync"),
            "latency_ms": etl.get("latency_ms", 100),
            "sync_rate_pct": etl.get("sync_rate_pct", 100.0),
            "missing_rows": etl.get("missing_rows", 0),
            "findings": etl.get("notes", "ETL sync verified clean."),
            "notes": etl.get("notes", "No ingestion pipeline anomalies detected."),
        }
    else:
        return {
            "status": "healthy",
            "anomaly_detected": False,
            "root_cause_confirmed": False,
            "job_name": "etl_sales_sync",
            "latency_ms": 95,
            "sync_rate_pct": 100.0,
            "missing_rows": 0,
            "findings": "ETL sync clean; normal latency.",
            "notes": f"No pipeline lag detected in {norm_reg} for {norm_wk}.",
        }


def check_pricing_changes(region: str, week: str) -> Dict[str, Any]:
    """Check SKU price schedules, discount overrides, and promo code activations."""
    norm_reg, norm_wk = normalize_region_and_week(region, week)
    case = CASES.get((norm_reg, norm_wk))

    if case and case.get("root_cause_tool") == "check_pricing_changes":
        pricing = case["pricing"]
        return {
            "status": "anomaly_found",
            "anomaly_detected": True,
            "root_cause_confirmed": True,
            "dollar_impact": pricing.get("dollar_impact"),
            "percent_impact": pricing.get("percent_impact"),
            "affected_product": pricing.get("affected_product"),
            "promo_code": pricing.get("promo_code"),
            "findings": pricing.get("findings"),
            "pricing_events": pricing.get("pricing_events", []),
            "notes": pricing.get("notes"),
        }
    elif case and "pricing" in case:
        pricing = case["pricing"]
        return {
            "status": "normal",
            "anomaly_detected": False,
            "root_cause_confirmed": False,
            "dollar_impact": 0,
            "percent_impact": 0,
            "pricing_events": pricing.get("pricing_events", []),
            "findings": pricing.get("notes", "No unauthorized price changes found."),
            "notes": pricing.get("notes", "Catalog pricing matches published master price sheet."),
        }
    else:
        return {
            "status": "normal",
            "anomaly_detected": False,
            "root_cause_confirmed": False,
            "dollar_impact": 0,
            "percent_impact": 0,
            "pricing_events": [],
            "findings": "No price or promo changes.",
            "notes": f"Standard pricing active for {norm_reg} during {norm_wk}.",
        }


def check_inventory_stockouts(region: str, week: str) -> Dict[str, Any]:
    """Check SKU inventory levels, out-of-stock events, and unfulfilled order backlog."""
    norm_reg, norm_wk = normalize_region_and_week(region, week)
    case = CASES.get((norm_reg, norm_wk))

    if case and case.get("root_cause_tool") == "check_inventory_stockouts":
        inv = case["inventory"]
        return {
            "status": "stockout_detected",
            "anomaly_detected": True,
            "root_cause_confirmed": True,
            "sku": inv.get("sku"),
            "product": inv.get("product"),
            "stockout_days": inv.get("stockout_days"),
            "current_stock": inv.get("current_stock"),
            "unfulfilled_backlog_units": inv.get("unfulfilled_backlog_units"),
            "dollar_impact": inv.get("dollar_impact"),
            "percent_impact": inv.get("percent_impact"),
            "findings": inv.get("findings"),
            "notes": inv.get("notes"),
        }
    elif case and "inventory" in case:
        inv = case["inventory"]
        return {
            "status": inv.get("status", "healthy"),
            "anomaly_detected": False,
            "root_cause_confirmed": False,
            "stockout_count": inv.get("stockout_count", 0),
            "unfulfilled_backlog": inv.get("unfulfilled_backlog", 0),
            "findings": inv.get("notes", "All items in stock."),
            "notes": inv.get("notes", "Fulfillment operational; safe buffer maintained."),
        }
    else:
        return {
            "status": "healthy",
            "anomaly_detected": False,
            "root_cause_confirmed": False,
            "stockout_count": 0,
            "unfulfilled_backlog": 0,
            "findings": "All inventory levels healthy.",
            "notes": f"Zero backlogged orders in {norm_reg} for {norm_wk}.",
        }


def check_competitor_promos(region: str, week: str) -> Dict[str, Any]:
    """Check competitor promotional campaigns, rival discount tiers, and ad blitzes."""
    norm_reg, norm_wk = normalize_region_and_week(region, week)

    # Check seeded West promo in W11
    if norm_reg == "West" and norm_wk == "2026-W11":
        return {
            "status": "active_campaign",
            "anomaly_detected": False,  # Not the root cause for our test inquiries unless asked
            "root_cause_confirmed": False,
            "active_promotions": [
                {
                    "competitor": "CloudScale Pro",
                    "campaign": "Spring Blitz 25% Off",
                    "territory": "West",
                }
            ],
            "findings": "Rival campaign 'CloudScale Pro 25% Off' active in West region.",
            "notes": "Competitor promotional blitz restricted to West coast accounts.",
        }

    case = CASES.get((norm_reg, norm_wk))
    if case and "competitor" in case:
        comp = case["competitor"]
        return {
            "status": "normal",
            "anomaly_detected": False,
            "root_cause_confirmed": False,
            "active_promotions": comp.get("active_promotions", []),
            "findings": comp.get("notes", "No competitor discounts detected."),
            "notes": comp.get("notes"),
        }

    return {
        "status": "normal",
        "anomaly_detected": False,
        "root_cause_confirmed": False,
        "active_promotions": [],
        "findings": "No competitor promo activity.",
        "notes": f"No promotional campaigns from competitors found in {norm_reg}.",
    }


def check_holiday_calendar(region: str, week: str) -> Dict[str, Any]:
    """Check regional bank, federal, and public holiday calendars."""
    norm_reg, norm_wk = normalize_region_and_week(region, week)

    # Check seeded East holiday in W09
    if norm_reg == "East" and norm_wk == "2026-W09":
        return {
            "status": "holiday_observed",
            "anomaly_detected": False,
            "root_cause_confirmed": False,
            "holidays": [
                {
                    "name": "Regional Founders Day",
                    "date": "2026-02-27",
                    "type": "Banking Holiday",
                }
            ],
            "findings": "Founders Day bank holiday observed in East on Friday.",
            "notes": "Banking settlement delayed by 1 business day in East.",
        }

    case = CASES.get((norm_reg, norm_wk))
    if case and "holiday" in case:
        hol = case["holiday"]
        return {
            "status": "normal",
            "anomaly_detected": False,
            "root_cause_confirmed": False,
            "holidays": hol.get("holidays", []),
            "findings": hol.get("notes", "No regional holidays."),
            "notes": hol.get("notes"),
        }

    return {
        "status": "normal",
        "anomaly_detected": False,
        "root_cause_confirmed": False,
        "holidays": [],
        "findings": "No holidays observed.",
        "notes": f"Full 5 business days in {norm_reg} for {norm_wk}.",
    }


TOOL_REGISTRY = {
    "check_etl_pipeline": check_etl_pipeline,
    "check_pricing_changes": check_pricing_changes,
    "check_inventory_stockouts": check_inventory_stockouts,
    "check_competitor_promos": check_competitor_promos,
    "check_holiday_calendar": check_holiday_calendar,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "check_etl_pipeline",
            "description": "Check sync status, row counts, job delays, and latency logs for data ingestion pipelines.",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "Sales territory/region (e.g., South, North, West, East)",
                    },
                    "week": {
                        "type": "string",
                        "description": "Calendar week code (e.g., 2026-W10, W11, 2026-W11 Monday)",
                    },
                },
                "required": ["region", "week"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_pricing_changes",
            "description": "Check SKU price adjustments, discount overrides, contract repricing, and promo code activations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "Sales territory/region (e.g., South, North, West, East)",
                    },
                    "week": {
                        "type": "string",
                        "description": "Calendar week code (e.g., 2026-W10, W12, W13)",
                    },
                },
                "required": ["region", "week"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_inventory_stockouts",
            "description": "Check SKU inventory stock levels, supply disruptions, and unfulfilled order backlogs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "Sales territory/region (e.g., South, North, West, East)",
                    },
                    "week": {
                        "type": "string",
                        "description": "Calendar week code (e.g., 2026-W11)",
                    },
                },
                "required": ["region", "week"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_competitor_promos",
            "description": "Check rival discounts, competitor ad blitzes, and promotional campaigns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "Sales territory/region (e.g., South, North, West, East)",
                    },
                    "week": {
                        "type": "string",
                        "description": "Calendar week code (e.g., 2026-W11)",
                    },
                },
                "required": ["region", "week"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_holiday_calendar",
            "description": "Check regional bank holidays, statutory holidays, and exchange closures.",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "Sales territory/region (e.g., South, North, West, East)",
                    },
                    "week": {
                        "type": "string",
                        "description": "Calendar week code (e.g., 2026-W09, W10)",
                    },
                },
                "required": ["region", "week"],
            },
        },
    },
]


def execute_tool(tool_name: str, region: str, week: str) -> Tuple[Dict[str, Any], int]:
    """Execute a tool by name with execution timing in ms."""
    fn = TOOL_REGISTRY.get(tool_name)
    if not fn:
        raise ValueError(f"Unknown tool: {tool_name}")

    start_t = time.perf_counter()
    result = fn(region, week)
    elapsed_ms = max(1, int((time.perf_counter() - start_t) * 1000))
    return result, elapsed_ms

