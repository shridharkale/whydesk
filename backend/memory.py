"""Hindsight memory integration and local fallback for WhyDesk."""

import uuid
import datetime
from typing import List, Dict, Any, Optional
from backend import config

try:
    from hindsight_client import Hindsight
    HINDSIGHT_AVAILABLE = True
except ImportError:
    HINDSIGHT_AVAILABLE = False


class LocalMemoryFallback:
    """In-memory fallback providing identical interface when HINDSIGHT_API_KEY is not set."""

    def __init__(self, bank_id: str = "whydesk-local-bank"):
        self.bank_id = bank_id
        self.memories: List[Dict[str, Any]] = []
        self.backend_type = "Local simulation"

    def ensure_bank(self) -> None:
        pass

    def recall_context(
        self, question: str, region: str, stakeholder: str
    ) -> Dict[str, Any]:
        q_lower = (question + " " + region + " " + stakeholder).lower()
        matched = []

        for m in self.memories:
            text_lower = m["text"].lower()
            ctx_lower = (m.get("context") or "").lower()
            reg_lower = region.lower()

            # Relevance match
            if (
                reg_lower in text_lower
                or reg_lower in ctx_lower
                or "data_pipeline_reliability" in ctx_lower
                or f"stakeholder_preference:{stakeholder.lower()}" in ctx_lower
                or ("monday" in q_lower and "monday" in text_lower)
                or ("pricing" in q_lower and "pricing" in text_lower)
            ):
                matched.append(m)

        # Reflection generation based on matched memories
        recall_query = f"{question} | region: {region} | stakeholder: {stakeholder}"
        reflect_query = (
            f"Given investigation question '{question}' for region '{region}' and stakeholder '{stakeholder}', "
            f"determine: 1) which 1-2 tools to run first, 2) which hypotheses to deprioritize, "
            f"3) pipeline reliability traps, and 4) stakeholder formatting constraints."
        )

        if not matched:
            reflection = (
                "COLD_START_NO_MEMORIES: No institutional memory exists for this region or product pattern. "
                "Recommended plan: Execute exhaustive baseline audit in standard order: "
                "check_holiday_calendar, check_competitor_promos, check_inventory_stockouts, "
                "check_pricing_changes, check_etl_pipeline."
            )
        else:
            has_etl_trap = any("etl" in m["text"].lower() or "pipeline" in m["text"].lower() for m in matched)
            has_pricing_cause = any("pricing" in m["text"].lower() or "discount" in m["text"].lower() for m in matched)
            has_finance_pref = any("finance" in (m.get("context") or "").lower() or "1-line" in m["text"].lower() for m in matched)

            plan_points = []
            if has_etl_trap and "monday" in q_lower:
                plan_points.append("Check check_etl_pipeline first to rule out Monday etl_sales_sync lag.")
            elif has_pricing_cause:
                plan_points.append("Prioritize check_etl_pipeline (sanity check) and check_pricing_changes.")
            else:
                plan_points.append("Check relevant operational tools based on confirmed regional history.")

            plan_points.append("Deprioritize holiday, competitor, and inventory if prior investigations ruled them out.")

            if stakeholder.lower() == "finance head" or has_finance_pref:
                plan_points.append("Formatting directive: Finance Head mandates exactly 1 line with the exact dollar impact.")
            else:
                plan_points.append(f"Formatting directive: Provide full diagnostic breakdown with tool trace for {stakeholder}.")

            reflection = (
                f"Recalled {len(matched)} institutional memories for {region}. "
                + " | ".join(plan_points)
            )

        return {
            "memories": matched,
            "reflection": reflection,
            "queries": {
                "recall_query": recall_query,
                "reflect_query": reflect_query,
            },
        }

    def retain_investigation(
        self,
        region: str,
        week: str,
        confirmed_cause: str,
        impact_str: str,
        ruled_out: List[str],
        is_etl_lag: bool = False,
        stakeholder: Optional[str] = None,
        stakeholder_format_pref: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        retained = []
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # (a) Verdict
        ruled_out_str = ", ".join(ruled_out) if ruled_out else "none"
        verdict_text = (
            f"In {week} for the {region} region, the confirmed root cause was "
            f"{confirmed_cause} (Impact: {impact_str}). Ruled-out: {ruled_out_str}."
        )
        verdict_mem = {
            "id": f"mem-{uuid.uuid4().hex[:8]}",
            "text": verdict_text,
            "type": "observation",
            "context": f"investigation_verdict:{region}",
            "mentioned_at": now_iso,
            "metadata": {
                "region": region,
                "week": week,
                "verdict": confirmed_cause,
                "impact": impact_str,
            },
        }
        self.memories.append(verdict_mem)
        retained.append(verdict_mem)

        # (b) Pipeline reliability note
        if is_etl_lag:
            etl_text = (
                "Monday revenue drops are often false alarms caused by etl_sales_sync lag; "
                "verify ETL health before trusting Monday anomalies."
            )
            etl_mem = {
                "id": f"mem-{uuid.uuid4().hex[:8]}",
                "text": etl_text,
                "type": "world",
                "context": "data_pipeline_reliability",
                "mentioned_at": now_iso,
                "metadata": {"pipeline": "etl_sales_sync", "trap": "Monday lag"},
            }
            self.memories.append(etl_mem)
            retained.append(etl_mem)

        # (c) Stakeholder preference
        if stakeholder and stakeholder_format_pref:
            pref_mem = {
                "id": f"mem-{uuid.uuid4().hex[:8]}",
                "text": f"{stakeholder} format preference: {stakeholder_format_pref}",
                "type": "experience",
                "context": f"stakeholder_preference:{stakeholder}",
                "mentioned_at": now_iso,
                "metadata": {"stakeholder": stakeholder},
            }
            self.memories.append(pref_mem)
            retained.append(pref_mem)

        return retained

    def list_memories(self) -> List[Dict[str, Any]]:
        return list(self.memories)

    def reset_bank(self) -> None:
        self.memories.clear()


class WhyDeskMemory:
    """Production memory wrapper managing institutional memory via Hindsight or local simulation."""

    def __init__(
        self,
        bank_id: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.bank_id = bank_id or config.HINDSIGHT_BANK_ID
        self.api_key = api_key or config.HINDSIGHT_API_KEY
        self.base_url = base_url or config.HINDSIGHT_BASE_URL
        self._fallback: Optional[LocalMemoryFallback] = None

        if HINDSIGHT_AVAILABLE and self.api_key:
            try:
                self.client: Optional[Hindsight] = Hindsight(
                    base_url=self.base_url,
                    api_key=self.api_key,
                    timeout=30.0,
                )
                self.backend_type = "Hindsight Cloud"
            except Exception:
                self.client = None
                self._fallback = LocalMemoryFallback(self.bank_id)
                self.backend_type = "Local simulation"
        else:
            self.client = None
            self._fallback = LocalMemoryFallback(self.bank_id)
            self.backend_type = "Local simulation"

    def ensure_bank(self) -> None:
        """Create bank if not exists, configuring mission and disposition."""
        if not self.client:
            if self._fallback:
                self._fallback.ensure_bank()
            return

        try:
            self.client.create_bank(
                bank_id=self.bank_id,
                name=config.BANK_NAME,
                mission=config.BANK_MISSION,
                disposition_skepticism=config.BANK_DISPOSITION["skepticism"],
                disposition_literalism=config.BANK_DISPOSITION["literalism"],
                disposition_empathy=config.BANK_DISPOSITION["empathy"],
            )
        except Exception as e:
            # Bank may already exist, which is expected
            err_msg = str(e).lower()
            if "already exists" not in err_msg and "409" not in err_msg:
                # Log but continue so service stays resilient
                pass

    def recall_context(
        self, question: str, region: str, stakeholder: str
    ) -> Dict[str, Any]:
        """Recall institutional memory and generate a strategic reflection plan."""
        if not self.client:
            return self._fallback.recall_context(question, region, stakeholder)

        recall_query = f"{question} region: {region} stakeholder: {stakeholder}"
        reflect_query = (
            f"Regarding the metric drop in {region} for question '{question}' presented to {stakeholder}: "
            f"1) Which 1-2 diagnostic tools should be checked first? "
            f"2) Which hypotheses have been ruled out previously and can be deprioritized? "
            f"3) What pipeline traps or data lag issues should we guard against? "
            f"4) How does stakeholder '{stakeholder}' require the final verdict to be formatted?"
        )

        memories: List[Dict[str, Any]] = []
        reflection = ""

        try:
            # SDK verified signature: bank_id, query, types, max_tokens, budget
            recall_resp = self.client.recall(
                bank_id=self.bank_id,
                query=recall_query,
                types=["world", "experience", "observation"],
                budget="mid",
                max_tokens=2048,
            )
            if recall_resp and hasattr(recall_resp, "results"):
                for r in recall_resp.results:
                    memories.append(
                        {
                            "id": getattr(r, "id", str(uuid.uuid4())),
                            "text": getattr(r, "text", ""),
                            "type": getattr(r, "type", "observation"),
                            "context": getattr(r, "context", ""),
                            "mentioned_at": str(getattr(r, "mentioned_at", "")),
                            "metadata": getattr(r, "metadata", {}) or {},
                        }
                    )
        except Exception as e:
            print(f"[Hindsight Recall Error]: {e}")
            import traceback
            traceback.print_exc()
            if self._fallback:
                return self._fallback.recall_context(question, region, stakeholder)

        try:
            reflect_resp = self.client.reflect(
                bank_id=self.bank_id,
                query=reflect_query,
                budget="mid",
                max_tokens=2048,
            )
            if reflect_resp and hasattr(reflect_resp, "text"):
                reflection = reflect_resp.text
        except Exception:
            # If reflection fails or is cold start, formulate plan from recalled memories
            if not memories:
                reflection = (
                    "COLD_START_NO_MEMORIES: No institutional memories found for this region. "
                    "Default audit required across all 5 diagnostic tools."
                )
            else:
                reflection = f"Recalled {len(memories)} institutional memories for {region}. Prioritize confirmed patterns."

        return {
            "memories": memories,
            "reflection": reflection,
            "queries": {
                "recall_query": recall_query,
                "reflect_query": reflect_query,
            },
        }

    def retain_investigation(
        self,
        region: str,
        week: str,
        confirmed_cause: str,
        impact_str: str,
        ruled_out: List[str],
        is_etl_lag: bool = False,
        stakeholder: Optional[str] = None,
        stakeholder_format_pref: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retain investigation verdict, pipeline notes, and format preferences synchronously."""
        if not self.client:
            return self._fallback.retain_investigation(
                region,
                week,
                confirmed_cause,
                impact_str,
                ruled_out,
                is_etl_lag,
                stakeholder,
                stakeholder_format_pref,
            )

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        retained_payloads = []

        # (a) Verdict
        ruled_out_str = ", ".join(ruled_out) if ruled_out else "none"
        verdict_text = (
            f"In {week} for the {region} region, the confirmed root cause was "
            f"{confirmed_cause} (Impact: {impact_str}). Ruled-out: {ruled_out_str}."
        )
        verdict_metadata = {
            "region": region,
            "week": week,
            "verdict": confirmed_cause,
            "impact": impact_str,
        }

        try:
            self.client.retain(
                bank_id=self.bank_id,
                content=verdict_text,
                context=f"investigation_verdict:{region}",
                metadata=verdict_metadata,
                retain_async=False,
            )
            retained_payloads.append(
                {
                    "text": verdict_text,
                    "type": "observation",
                    "context": f"investigation_verdict:{region}",
                    "metadata": verdict_metadata,
                    "mentioned_at": now_iso,
                }
            )
        except Exception:
            pass

        # (b) Pipeline reliability note
        if is_etl_lag:
            etl_text = (
                "Monday revenue drops are often false alarms caused by etl_sales_sync lag; "
                "verify ETL health before trusting Monday anomalies."
            )
            try:
                self.client.retain(
                    bank_id=self.bank_id,
                    content=etl_text,
                    context="data_pipeline_reliability",
                    metadata={"pipeline": "etl_sales_sync", "trap": "Monday lag"},
                    retain_async=False,
                )
                retained_payloads.append(
                    {
                        "text": etl_text,
                        "type": "world",
                        "context": "data_pipeline_reliability",
                        "metadata": {"pipeline": "etl_sales_sync", "trap": "Monday lag"},
                        "mentioned_at": now_iso,
                    }
                )
            except Exception:
                pass

        # (c) Stakeholder format preference
        if stakeholder and stakeholder_format_pref:
            pref_text = f"{stakeholder} format preference: {stakeholder_format_pref}"
            try:
                self.client.retain(
                    bank_id=self.bank_id,
                    content=pref_text,
                    context=f"stakeholder_preference:{stakeholder}",
                    metadata={"stakeholder": stakeholder},
                    retain_async=False,
                )
                retained_payloads.append(
                    {
                        "text": pref_text,
                        "type": "experience",
                        "context": f"stakeholder_preference:{stakeholder}",
                        "metadata": {"stakeholder": stakeholder},
                        "mentioned_at": now_iso,
                    }
                )
            except Exception:
                pass

        return retained_payloads

    def list_memories(self) -> List[Dict[str, Any]]:
        """List all memories stored in the bank."""
        if not self.client:
            return self._fallback.list_memories()

        try:
            resp = self.client.list_memories(bank_id=self.bank_id, limit=100)
            items = []
            if resp and hasattr(resp, "items"):
                for item in resp.items:
                    items.append(
                        {
                            "id": getattr(item, "id", ""),
                            "text": getattr(item, "text", ""),
                            "type": getattr(item, "type", "observation"),
                            "context": getattr(item, "context", ""),
                            "mentioned_at": str(getattr(item, "mentioned_at", "")),
                            "metadata": getattr(item, "metadata", {}) or {},
                        }
                    )
            return items
        except Exception:
            return []

    def reset_bank(self) -> None:
        """Reset the memory bank (delete or purge)."""
        if not self.client:
            self._fallback.reset_bank()
            return

        try:
            self.client.delete_bank(bank_id=self.bank_id)
        except Exception:
            pass

        # Re-initialize clean bank
        self.ensure_bank()

