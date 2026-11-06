"""Synthetic business data and deterministic anomaly cases for WhyDesk."""

from typing import Dict, Any, List

REGIONS = ["South", "North", "West", "East"]
PRODUCTS = ["Core SaaS", "Enterprise Add-on", "API Tier"]

# Deterministic anomaly cases
CASES: Dict[str, Dict[str, Any]] = {
    # Case 1: South W10
    ("South", "2026-W10"): {
        "case_id": 1,
        "region": "South",
        "week": "2026-W10",
        "revenue_change_pct": -18.0,
        "impact_dollars": -42500,
        "root_cause_tool": "check_pricing_changes",
        "root_cause_summary": "Unannounced 20% discount tier auto-applied on Core SaaS renewals.",
        "etl": {
            "status": "healthy",
            "job": "etl_sales_sync",
            "latency_ms": 112,
            "sync_rate_pct": 100.0,
            "missing_rows": 0,
            "notes": "All ETL pipelines operating normally. No synchronization delays detected.",
        },
        "pricing": {
            "anomaly_detected": True,
            "root_cause_confirmed": True,
            "dollar_impact": -42500,
            "percent_impact": -18.0,
            "affected_product": "Core SaaS",
            "findings": "Unannounced 20% discount tier auto-applied on Core SaaS renewals.",
            "pricing_events": [
                {
                    "event_type": "Auto-applied Discount Tier",
                    "product": "Core SaaS",
                    "tier": "Renewal Protection Tier B",
                    "discount_rate": "20%",
                    "impact": "-$42,500 WoW",
                }
            ],
            "notes": "Configuration error in renewal billing script auto-discounted 342 enterprise renewals.",
        },
        "inventory": {
            "status": "healthy",
            "stockout_count": 0,
            "unfulfilled_backlog": 0,
            "notes": "All product tiers and physical tokens at standard inventory levels.",
        },
        "competitor": {
            "active_promotions": [],
            "notes": "No competitor discount campaigns detected in South region.",
        },
        "holiday": {
            "holidays": [],
            "notes": "No regional bank or public holidays in South during 2026-W10.",
        },
    },

    # Case 2: South W11 (Monday lag)
    ("South", "2026-W11"): {
        "case_id": 2,
        "region": "South",
        "week": "2026-W11",
        "revenue_change_pct": -64.0,
        "impact_dollars": 0,
        "delayed_dollars": 88000,
        "root_cause_tool": "check_etl_pipeline",
        "root_cause_summary": "Data-pipeline lag: etl_sales_sync job stalled at 02:00 UTC, 65% of Monday rows missing ($88,000 delayed in ETL, $0 real loss).",
        "etl": {
            "anomaly_detected": True,
            "root_cause_confirmed": True,
            "status": "degraded",
            "job": "etl_sales_sync",
            "stall_time_utc": "02:00 UTC",
            "missing_rows_pct": 65.0,
            "delayed_revenue": 88000,
            "real_loss": 0,
            "dollar_impact": 0,
            "percent_impact": -64.0,
            "findings": "Data-pipeline lag: etl_sales_sync job stalled at 02:00 UTC; 65% of Monday rows are missing ($88,000 delayed in ETL, $0 real loss).",
            "notes": "Stalled thread in South Kafka ingestion worker. Recovery in progress; raw logs confirm uningested transactions.",
        },
        "pricing": {
            "anomaly_detected": False,
            "root_cause_confirmed": False,
            "pricing_events": [],
            "notes": "Standard catalog pricing active. No price overrides or discount tiers applied.",
        },
        "inventory": {
            "status": "healthy",
            "stockout_count": 0,
            "unfulfilled_backlog": 0,
            "notes": "Normal fulfillment across all product tiers.",
        },
        "competitor": {
            "active_promotions": [],
            "notes": "No rival promotions active in South (note: CloudScale Pro promo active in West only).",
        },
        "holiday": {
            "holidays": [],
            "notes": "No regional holidays in South during 2026-W11.",
        },
    },

    # Case 3: North W11 (Hardware stockout)
    ("North", "2026-W11"): {
        "case_id": 3,
        "region": "North",
        "week": "2026-W11",
        "revenue_change_pct": -24.0,
        "impact_dollars": -31200,
        "root_cause_tool": "check_inventory_stockouts",
        "root_cause_summary": "Stockout of SKU ENT-GATEWAY-02 with zero inventory for 5 days.",
        "etl": {
            "status": "healthy",
            "job": "etl_sales_sync",
            "latency_ms": 105,
            "sync_rate_pct": 100.0,
            "missing_rows": 0,
            "notes": "North ingestion queue clean with zero dropped rows.",
        },
        "pricing": {
            "anomaly_detected": False,
            "root_cause_confirmed": False,
            "pricing_events": [],
            "notes": "Catalog pricing unchanged across North region.",
        },
        "inventory": {
            "anomaly_detected": True,
            "root_cause_confirmed": True,
            "sku": "ENT-GATEWAY-02",
            "product": "Enterprise Add-on (Hardware Bundle)",
            "stockout_days": 5,
            "current_stock": 0,
            "unfulfilled_backlog_units": 142,
            "dollar_impact": -31200,
            "percent_impact": -24.0,
            "findings": "Stockout of SKU ENT-GATEWAY-02: zero inventory for 5 days, resulting in 142 backlogged orders.",
            "notes": "Supplier transit disruption halted ENT-GATEWAY-02 deliveries to Chicago distribution center.",
        },
        "competitor": {
            "active_promotions": [],
            "notes": "No competitor campaign in North (competitor CloudScale Pro is active in West only).",
        },
        "holiday": {
            "holidays": [],
            "notes": "No regional holidays in North during 2026-W11.",
        },
    },

    # Case 4: South W12 (Legacy promo code SOUTH-Q1-25)
    ("South", "2026-W12"): {
        "case_id": 4,
        "region": "South",
        "week": "2026-W12",
        "revenue_change_pct": -15.0,
        "impact_dollars": -36800,
        "root_cause_tool": "check_pricing_changes",
        "root_cause_summary": "Legacy promo code SOUTH-Q1-25 reactivated by mistake on API Tier.",
        "etl": {
            "status": "healthy",
            "job": "etl_sales_sync",
            "latency_ms": 98,
            "sync_rate_pct": 100.0,
            "missing_rows": 0,
            "notes": "ETL sync is fully healthy; row counts match transactional database.",
        },
        "pricing": {
            "anomaly_detected": True,
            "root_cause_confirmed": True,
            "promo_code": "SOUTH-Q1-25",
            "affected_product": "API Tier",
            "dollar_impact": -36800,
            "percent_impact": -15.0,
            "findings": "Legacy promo code SOUTH-Q1-25 reactivated by mistake on API Tier.",
            "pricing_events": [
                {
                    "event_type": "Erroneous Promo Code Activation",
                    "promo_code": "SOUTH-Q1-25",
                    "product": "API Tier",
                    "discount_value": "35% off high-volume usage",
                    "impact": "-$36,800 WoW",
                }
            ],
            "notes": "Deprecate flag expired in coupon engine, re-enabling SOUTH-Q1-25 across South accounts.",
        },
        "inventory": {
            "status": "healthy",
            "stockout_count": 0,
            "unfulfilled_backlog": 0,
            "notes": "All inventory levels nominal.",
        },
        "competitor": {
            "active_promotions": [],
            "notes": "No rival promotions in South during 2026-W12.",
        },
        "holiday": {
            "holidays": [],
            "notes": "No holidays during 2026-W12 in South.",
        },
    },

    # Case 5: South W13 (Reseller contract repricing)
    ("South", "2026-W13"): {
        "case_id": 5,
        "region": "South",
        "week": "2026-W13",
        "revenue_change_pct": -19.0,
        "impact_dollars": -47900,
        "root_cause_tool": "check_pricing_changes",
        "root_cause_summary": "Regional reseller contract repricing cut unit ACV by 19% (ETL sync verified clean).",
        "etl": {
            "status": "healthy",
            "job": "etl_sales_sync",
            "latency_ms": 102,
            "sync_rate_pct": 100.0,
            "missing_rows": 0,
            "notes": "ETL sync verified clean. 100% of event records accounted for.",
        },
        "pricing": {
            "anomaly_detected": True,
            "root_cause_confirmed": True,
            "dollar_impact": -47900,
            "percent_impact": -19.0,
            "affected_product": "Core SaaS & Enterprise Add-on (Reseller Channel)",
            "findings": "Regional reseller contract repricing cut unit ACV by 19%; ETL sync verified clean.",
            "pricing_events": [
                {
                    "event_type": "Reseller Master Agreement Amendment",
                    "contract_id": "RESELLER-SOUTH-2026",
                    "renegotiation": "19% ACV cut across renewed reseller seats",
                    "impact": "-$47,900 WoW",
                }
            ],
            "notes": "Amended tier schedules took effect April 1st with Southern VAR network.",
        },
        "inventory": {
            "status": "healthy",
            "stockout_count": 0,
            "unfulfilled_backlog": 0,
            "notes": "Inventory and fulfillment metrics nominal.",
        },
        "competitor": {
            "active_promotions": [],
            "notes": "No rival discount campaigns detected in South region.",
        },
        "holiday": {
            "holidays": [],
            "notes": "No regional bank holidays in South during 2026-W13.",
        },
    },
}

# Baseline structured data for general queries
OTHER_SEEDED_EVENTS: List[Dict[str, Any]] = [
    {
        "type": "competitor",
        "region": "West",
        "week": "2026-W11",
        "campaign": "CloudScale Pro Spring Blitz (25% off)",
        "notes": "Aggressive West coast rival discount campaign.",
    },
    {
        "type": "holiday",
        "region": "East",
        "week": "2026-W09",
        "holiday": "Regional Founders Day (Banking Holiday)",
        "notes": "East financial exchanges closed on Friday.",
    },
]


def normalize_region_and_week(region_input: str, week_input: str) -> tuple[str, str]:
    """Normalize region name and week code."""
    reg = region_input.strip().capitalize()
    for valid in REGIONS:
        if valid.lower() in region_input.lower():
            reg = valid
            break

    # Normalize week: look for W10, W11, W12, W13, W09, etc.
    import re
    match = re.search(r"W(\d{1,2})", week_input, re.IGNORECASE)
    if match:
        week_num = int(match.group(1))
        norm_week = f"2026-W{week_num:02d}"
    else:
        norm_week = week_input.strip()

    return reg, norm_week

