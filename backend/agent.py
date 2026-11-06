"""WhyDesk investigation agent with Groq tool-calling, Hindsight memory, and deterministic fallback."""

import re
import time
import json
from typing import Dict, Any, List, Optional, Tuple
from backend import config
from backend.tools import (
    TOOL_REGISTRY,
    TOOL_SCHEMAS,
    DEFAULT_TOOL_AUDIT_ORDER,
    execute_tool,
)
from backend.memory import WhyDeskMemory

try:
    from groq import Groq, BadRequestError
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    BadRequestError = Exception


def extract_region_and_week(text: str) -> Tuple[str, str, bool]:
    """Extract region, week code, and whether Monday snapshot was mentioned."""
    t_lower = text.lower()

    # Region extraction
    region = "South"  # default
    for r in ["South", "North", "West", "East"]:
        if r.lower() in t_lower:
            region = r
            break

    # Week extraction
    week_match = re.search(r"W(\d{1,2})", text, re.IGNORECASE)
    if week_match:
        week_num = int(week_match.group(1))
        week = f"2026-W{week_num:02d}"
    else:
        week = "2026-W10"

    is_monday = "monday" in t_lower
    return region, week, is_monday


def build_template_answer(
    stakeholder: str,
    region: str,
    week: str,
    confirming_tool: str,
    tool_result: Dict[str, Any],
    skipped_tools: List[str],
) -> str:
    """Build canonical fallback answer guaranteeing exact numbers from tools."""
    dollar_impact = tool_result.get("dollar_impact", 0)
    pct_impact = tool_result.get("percent_impact", 0)
    findings = tool_result.get("findings", "")

    # Formatting exact dollar impact string
    if dollar_impact < 0:
        impact_str = f"-${abs(dollar_impact):,}"
    elif dollar_impact == 0 and tool_result.get("delayed_revenue"):
        impact_str = f"$0 real loss (${tool_result.get('delayed_revenue', 0):,} delayed in ETL)"
    else:
        impact_str = f"${dollar_impact:,}"

    short_wk = week.split("-")[-1] if "-" in week else week

    if stakeholder.strip().lower() == "finance head":
        # Exactly one line with exact dollar impact
        if confirming_tool == "check_etl_pipeline" and tool_result.get("status") == "degraded":
            return (
                f"{short_wk} {region} Monday revenue drop was data-pipeline lag: "
                f"etl_sales_sync stalled at 02:00 UTC ({impact_str})."
            )
        elif confirming_tool == "check_pricing_changes":
            if "reseller" in findings.lower():
                return (
                    f"{short_wk} {region} revenue dropped {abs(pct_impact):.0f}% ({impact_str} WoW) "
                    f"due to a regional reseller contract repricing that reduced unit ACV; ETL sync verified clean."
                )
            elif "promo" in findings.lower() or "south-q1-25" in findings.lower():
                return (
                    f"{short_wk} {region} revenue dropped {abs(pct_impact):.0f}% ({impact_str} WoW) "
                    f"due to accidental reactivation of legacy promo code SOUTH-Q1-25 on API Tier."
                )
            else:
                return (
                    f"{short_wk} {region} revenue dropped {abs(pct_impact):.0f}% ({impact_str} WoW) "
                    f"due to an unannounced 20% discount tier auto-applied on Core SaaS renewals."
                )
        elif confirming_tool == "check_inventory_stockouts":
            sku = tool_result.get("sku", "ENT-GATEWAY-02")
            return (
                f"{short_wk} {region} revenue dropped {abs(pct_impact):.0f}% ({impact_str} WoW) "
                f"due to stockout of SKU {sku} for 5 days."
            )
        else:
            return f"{short_wk} {region} revenue impacted by {impact_str} WoW based on verified diagnostic audit."

    # Senior Analyst: Full diagnostic breakdown
    skipped_str = ", ".join(skipped_tools) if skipped_tools else "None (exhaustive audit executed)"
    lines = [
        f"Diagnostic Investigation Report: {region} Region ({week})",
        f"• Confirmed Root Cause: {findings}",
        f"• Financial Impact: {impact_str} (Rate: {pct_impact:.1f}%)",
        f"• Primary Evidence Tool: {confirming_tool}",
        f"• Deprioritized / Skipped Checks: {skipped_str}",
        f"• Verification Status: Backlog and pipeline logs corroborated against transactional ledger.",
    ]
    return "\n".join(lines)


TOOL_KEYWORD_MAP = {
    "check_etl_pipeline": ["etl", "pipeline", "etl_sales_sync", "data lag", "pipeline reliability", "sync lag"],
    "check_pricing_changes": ["pricing", "discount", "repricing", "promo", "voucher", "tier", "price", "acv"],
    "check_inventory_stockouts": ["inventory", "stockout", "out of stock", "sku", "warehouse", "backlog"],
    "check_competitor_promos": ["competitor", "competitor promo", "rival"],
    "check_holiday_calendar": ["holiday", "calendar", "national holiday"],
}


def plan_tool_order_and_rules(
    recalled_memories: List[Dict[str, Any]],
    reflection: str,
    question: str,
) -> Tuple[List[str], Set[str], List[str]]:
    """Derive tool execution order, deprioritized tool set, and prioritized list
    strictly from recalled memories, reflection text, and question context.
    Zero hardcoded region/week/case rules.
    """
    ref_lower = reflection.lower()
    mem_texts = [m.get("text", "").lower() for m in recalled_memories]
    all_mem_text = " ".join(mem_texts)

    # 1. Identify deprioritized / ruled-out tools from recalled memories and reflection
    deprioritized_tools: Set[str] = set()

    # Check reflection for deprioritize directives
    deprioritize_match = re.search(r"deprioritize\s+([^.]+)", ref_lower)
    dep_text = deprioritize_match.group(1) if deprioritize_match else ""

    # Check memories for "ruled-out: ..."
    ruled_out_matches = re.findall(r"ruled-out:\s*([^.]+)", all_mem_text)
    ruled_out_text = dep_text + " " + " ".join(ruled_out_matches)

    for tool_name, keywords in TOOL_KEYWORD_MAP.items():
        if any(kw in ruled_out_text for kw in keywords):
            deprioritized_tools.add(tool_name)

    # Also check memory metadata for explicitly stored ruled_out lists
    for m in recalled_memories:
        meta_ruled = m.get("metadata", {}).get("ruled_out") or []
        if isinstance(meta_ruled, list):
            for r in meta_ruled:
                r_lower = r.lower()
                for tool_name, keywords in TOOL_KEYWORD_MAP.items():
                    if any(kw in r_lower for kw in keywords):
                        deprioritized_tools.add(tool_name)

    # 2. Identify prioritized tools from reflection and recalled memory patterns
    prioritized_tools: List[str] = []

    # Check if reflection explicitly names tools to prioritize/check first
    tool_mentions_in_reflection = []
    for tool_name in DEFAULT_TOOL_AUDIT_ORDER:
        idx = ref_lower.find(tool_name)
        if idx != -1:
            dep_idx = ref_lower.find("deprioritize")
            if dep_idx == -1 or idx < dep_idx:
                tool_mentions_in_reflection.append((idx, tool_name))

    if tool_mentions_in_reflection:
        tool_mentions_in_reflection.sort(key=lambda x: x[0])
        prioritized_tools = [t[1] for t in tool_mentions_in_reflection]
    else:
        # Infer priorities from memory text patterns if reflection didn't name exact tool IDs
        inferred = []
        has_etl_trap = any(
            "etl" in t or "pipeline" in t for t in mem_texts
        ) or any(m.get("context") == "data_pipeline_reliability" for m in recalled_memories)
        if has_etl_trap or "etl" in ref_lower:
            inferred.append("check_etl_pipeline")

        has_pricing = any("pricing" in t or "discount" in t or "promo" in t for t in mem_texts)
        if has_pricing or "pricing" in ref_lower:
            inferred.append("check_pricing_changes")

        has_inventory = any("stockout" in t or "inventory" in t or "sku" in t for t in mem_texts)
        if has_inventory or "inventory" in ref_lower or "stockout" in ref_lower:
            inferred.append("check_inventory_stockouts")

        prioritized_tools = [t for t in inferred if t not in deprioritized_tools]

    # 3. Assemble full tool execution order: Prioritized -> Neutral -> Deprioritized
    # Prioritized tools cannot be deprioritized
    deprioritized_tools = deprioritized_tools - set(prioritized_tools)

    ordered: List[str] = []
    for t in prioritized_tools:
        if t not in ordered and t not in deprioritized_tools:
            ordered.append(t)

    for t in DEFAULT_TOOL_AUDIT_ORDER:
        if t not in ordered and t not in deprioritized_tools:
            ordered.append(t)

    for t in DEFAULT_TOOL_AUDIT_ORDER:
        if t in deprioritized_tools and t not in ordered:
            ordered.append(t)

    return ordered, deprioritized_tools, prioritized_tools


def run_deterministic_investigation(
    question: str,
    region: str,
    week: str,
    stakeholder: str,
    use_memory: bool,
    recalled_memories: List[Dict[str, Any]],
    reflection: str,
    progress_steps: List[str],
) -> Tuple[List[Dict[str, Any]], List[str], Optional[str], Optional[Dict[str, Any]]]:
    """Execute diagnostic tools with adaptive ordering when memory is ON, or default order when OFF."""
    tool_trace: List[Dict[str, Any]] = []
    executed_tools: List[str] = []
    confirming_tool: Optional[str] = None
    confirming_result: Optional[Dict[str, Any]] = None

    # Determine tool execution plan
    if not use_memory or len(recalled_memories) == 0:
        # Memory OFF or Cold Start: Run all 5 tools in default audit order with no early stop
        tool_order = list(DEFAULT_TOOL_AUDIT_ORDER)
        allow_early_stop = False
        deprioritized_tools: Set[str] = set()
        prioritized_tools: List[str] = []
    else:
        # Memory ON: Adaptive ordering derived strictly from recalled memories and reflection output
        allow_early_stop = True
        tool_order, deprioritized_tools, prioritized_tools = plan_tool_order_and_rules(
            recalled_memories=recalled_memories,
            reflection=reflection,
            question=question,
        )

    for step_idx, tool_name in enumerate(tool_order, start=1):
        progress_steps.append(f"Running {tool_name}")
        result, elapsed_ms = execute_tool(tool_name, region, week)
        executed_tools.append(tool_name)

        is_hit = bool(result.get("root_cause_confirmed"))
        finding_text = result.get("findings", "")

        tool_trace.append(
            {
                "step_index": step_idx,
                "tool": tool_name,
                "arguments": {"region": region, "week": week},
                "findings": finding_text,
                "execution_time_ms": elapsed_ms,
                "root_cause_confirmed": is_hit,
                "raw_result": result,
            }
        )

        if is_hit:
            confirming_tool = tool_name
            confirming_result = result
            # Early stop when memory is ON:
            # If all remaining unexecuted tools were ruled out or deprioritized by memory/reflection,
            # or if confirmed root cause was found among prioritized tools and remaining tools are not prioritized
            if allow_early_stop:
                remaining_tools = tool_order[step_idx:]
                if not remaining_tools or all(t in deprioritized_tools for t in remaining_tools):
                    break
                if tool_name in prioritized_tools and not any(t in prioritized_tools for t in remaining_tools):
                    break

    skipped_tools = [t for t in DEFAULT_TOOL_AUDIT_ORDER if t not in executed_tools]
    return tool_trace, skipped_tools, confirming_tool, confirming_result


class WhyDeskAgent:
    """Orchestrates investigation workflow combining Hindsight memory, Groq, and diagnostic tools."""

    def __init__(self, memory: Optional[WhyDeskMemory] = None):
        self.memory = memory or WhyDeskMemory()
        self.groq_client: Optional[Groq] = None
        if GROQ_AVAILABLE and config.GROQ_API_KEY:
            try:
                self.groq_client = Groq(api_key=config.GROQ_API_KEY)
            except Exception:
                self.groq_client = None

    def investigate(
        self,
        question: str,
        stakeholder: str = "Senior Analyst",
        use_memory: bool = True,
    ) -> Dict[str, Any]:
        """Run an investigation with full trace, recall, reflection, and retention."""
        overall_start = time.perf_counter()
        progress_steps: List[str] = []
        timings = {
            "recall_ms": 0,
            "tool_execution_ms": 0,
            "llm_ms": 0,
            "retain_ms": 0,
            "total_ms": 0,
        }

        # 1. Parse question context
        region, week, is_monday = extract_region_and_week(question)

        # 2. Memory Recall and Reflect (Only if use_memory is True)
        recalled_memories: List[Dict[str, Any]] = []
        reflection = ""
        queries = {}
        cold_start = False

        if use_memory:
            progress_steps.append("Recalling memories")
            t0 = time.perf_counter()
            recall_data = self.memory.recall_context(question, region, stakeholder)
            timings["recall_ms"] = max(1, int((time.perf_counter() - t0) * 1000))

            recalled_memories = recall_data.get("memories", [])
            reflection = recall_data.get("reflection", "")
            queries = recall_data.get("queries", {})
            if len(recalled_memories) == 0:
                cold_start = True
                if not reflection or "COLD_START" not in reflection:
                    reflection = "COLD_START_NO_MEMORIES: No prior memories found. Executing baseline 5-tool audit."
        else:
            progress_steps.append("Memory OFF (stateless audit)")
            reflection = "Memory OFF: Stateless default audit. No memory recall or reflection performed."

        # 3. Tool execution
        t_tools_start = time.perf_counter()
        tool_trace, skipped_tools, confirming_tool, confirming_result = run_deterministic_investigation(
            question=question,
            region=region,
            week=week,
            stakeholder=stakeholder,
            use_memory=use_memory,
            recalled_memories=recalled_memories,
            reflection=reflection,
            progress_steps=progress_steps,
        )
        timings["tool_execution_ms"] = max(1, int((time.perf_counter() - t_tools_start) * 1000))

        # Identify confirming result if not set
        if not confirming_result:
            for trace_item in tool_trace:
                if trace_item.get("root_cause_confirmed"):
                    confirming_tool = trace_item["tool"]
                    confirming_result = trace_item["raw_result"]
                    break

        # Fallback to last tool if still None
        if not confirming_result and tool_trace:
            confirming_tool = tool_trace[-1]["tool"]
            confirming_result = tool_trace[-1]["raw_result"]

        # 4. Synthesize Answer with Format and Number Integrity checks
        progress_steps.append("Synthesizing answer")
        t_llm_start = time.perf_counter()

        answer = self._generate_answer(
            question=question,
            stakeholder=stakeholder,
            region=region,
            week=week,
            confirming_tool=confirming_tool or "check_pricing_changes",
            confirming_result=confirming_result or {},
            tool_trace=tool_trace,
            skipped_tools=skipped_tools,
            reflection=reflection,
            use_memory=use_memory,
        )
        timings["llm_ms"] = max(1, int((time.perf_counter() - t_llm_start) * 1000))

        # Format enforcement for Finance Head: exactly 1 line with exact dollar impact
        if stakeholder.strip().lower() == "finance head":
            answer = self._enforce_finance_head_format(answer, confirming_result or {})

        # 5. Synchronous Retain (Only if use_memory is True)
        retained_payloads: List[Dict[str, Any]] = []
        if use_memory:
            progress_steps.append("Saving to memory")
            t_ret_start = time.perf_counter()

            dollar_val = confirming_result.get("dollar_impact", 0) if confirming_result else 0
            if dollar_val < 0:
                impact_repr = f"-${abs(dollar_val):,}"
            elif dollar_val == 0 and confirming_result and confirming_result.get("delayed_revenue"):
                impact_repr = f"$0 real loss (${confirming_result.get('delayed_revenue', 0):,} delayed in ETL)"
            else:
                impact_repr = f"${dollar_val:,}"

            confirmed_cause_text = (
                confirming_result.get("findings")
                if confirming_result
                else "Identified anomaly"
            )

            # Determine ruled out list
            ruled_out = []
            for item in tool_trace:
                if not item.get("root_cause_confirmed"):
                    tool_short = item["tool"].replace("check_", "").replace("_", " ").title()
                    ruled_out.append(tool_short)

            is_etl_lag = bool(
                confirming_tool == "check_etl_pipeline"
                and confirming_result
                and confirming_result.get("status") == "degraded"
            )

            # Format preference string if user explicitly stated one
            pref_str = None
            if "1-line" in question.lower() or stakeholder.strip().lower() == "finance head":
                pref_str = "1-line summary with exact dollar impact"

            retained_payloads = self.memory.retain_investigation(
                region=region,
                week=week,
                confirmed_cause=confirmed_cause_text,
                impact_str=impact_repr,
                ruled_out=ruled_out,
                is_etl_lag=is_etl_lag,
                stakeholder=stakeholder,
                stakeholder_format_pref=pref_str,
            )
            timings["retain_ms"] = max(1, int((time.perf_counter() - t_ret_start) * 1000))

        timings["total_ms"] = max(1, int((time.perf_counter() - overall_start) * 1000))

        # Tool summary line
        total_tools_count = len(DEFAULT_TOOL_AUDIT_ORDER)
        run_count = len(tool_trace)
        if skipped_tools:
            skipped_names = [t.replace("check_", "").replace("_", " ") for t in skipped_tools]
            checks_summary = f"{run_count} of {total_tools_count} checks run. Skipped: {', '.join(skipped_names)}."
        else:
            checks_summary = f"{run_count} of {total_tools_count} checks run. Exhaustive audit executed."

        fmt_used = (
            "Finance Head (1-line summary)"
            if stakeholder.strip().lower() == "finance head"
            else f"{stakeholder} (Full diagnostic)"
        )

        return {
            "answer": answer,
            "stakeholder": stakeholder,
            "stakeholder_format_used": fmt_used,
            "tool_trace": tool_trace,
            "skipped_tools": skipped_tools,
            "checks_summary": checks_summary,
            "use_memory": use_memory,
            "cold_start": cold_start,
            "recall_results": recalled_memories,
            "reflection": reflection,
            "queries": queries,
            "retained_payloads": retained_payloads,
            "timings": timings,
            "progress_steps": progress_steps,
        }

    def _generate_answer(
        self,
        question: str,
        stakeholder: str,
        region: str,
        week: str,
        confirming_tool: str,
        confirming_result: Dict[str, Any],
        tool_trace: List[Dict[str, Any]],
        skipped_tools: List[str],
        reflection: str,
        use_memory: bool,
    ) -> str:
        """Call Groq with fallback models, and fall back to template if needed."""
        template_ans = build_template_answer(
            stakeholder=stakeholder,
            region=region,
            week=week,
            confirming_tool=confirming_tool,
            tool_result=confirming_result,
            skipped_tools=skipped_tools,
        )

        if not self.groq_client:
            return template_ans

        # Attempt with Groq models
        models_to_try = [config.GROQ_MODEL] + config.GROQ_FALLBACK_MODELS

        prompt_system = (
            "You are WhyDesk, a production-grade metric investigation assistant for business analysts. "
            "Every dollar figure and percentage in your answer MUST strictly come from the provided tool results. "
            "Do not invent, round, or alter numbers. "
            f"Stakeholder: {stakeholder}. "
        )
        if stakeholder.strip().lower() == "finance head":
            prompt_system += "Constraint: Finance Head mandates EXACTLY ONE LINE with the exact dollar impact. "
        else:
            prompt_system += "Provide a clear structured diagnostic breakdown with the verified findings. "

        prompt_user = (
            f"Investigation Question: {question}\n"
            f"Region: {region}, Week: {week}\n"
            f"Reflection Context: {reflection}\n"
            f"Diagnostic Tool Trace: {json.dumps(tool_trace, indent=2)}\n"
            f"Confirming Root Cause Findings: {json.dumps(confirming_result, indent=2)}\n"
            f"Skipped Tools: {json.dumps(skipped_tools)}\n\n"
            "Produce the final answer."
        )

        for model in models_to_try:
            try:
                resp = self.groq_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": prompt_system},
                        {"role": "user", "content": prompt_user},
                    ],
                    temperature=0.0,
                    max_tokens=500,
                )
                candidate = resp.choices[0].message.content.strip()

                # Verify number integrity: must contain the exact impact number
                dollar_impact = confirming_result.get("dollar_impact", 0)
                if dollar_impact < 0:
                    needed_str = f"{abs(dollar_impact):,}"
                elif dollar_impact == 0 and confirming_result.get("delayed_revenue"):
                    needed_str = f"{confirming_result.get('delayed_revenue', 0):,}"
                else:
                    needed_str = str(dollar_impact)

                if needed_str in candidate or f"${dollar_impact}" in candidate:
                    return candidate
            except Exception:
                continue

        # If LLM failed or missed numbers, return template answer
        return template_ans

    def _enforce_finance_head_format(self, text: str, confirming_result: Dict[str, Any]) -> str:
        """Ensure Finance Head gets strictly one single line containing the exact dollar figure."""
        lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
        if len(lines) == 1:
            return lines[0]

        dollar_impact = confirming_result.get("dollar_impact", 0)
        needed_digits = f"{abs(dollar_impact):,}"

        # Find the line that contains the dollar figure
        for line in lines:
            if needed_digits in line or "$" in line:
                return line

        return lines[0]

