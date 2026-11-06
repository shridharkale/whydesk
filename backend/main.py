"""FastAPI backend application for WhyDesk."""

from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend import config
from backend.agent import WhyDeskAgent
from backend.memory import WhyDeskMemory

app = FastAPI(title="WhyDesk API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
memory = WhyDeskMemory()
memory.ensure_bank()
agent = WhyDeskAgent(memory=memory)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
INDEX_FILE = FRONTEND_DIR / "index.html"


class InvestigateRequest(BaseModel):
    question: str = Field(..., description="The analyst inquiry or metric alert")
    stakeholder: str = Field(default="Senior Analyst", description="Stakeholder audience (Finance Head or Senior Analyst)")
    use_memory: bool = Field(default=True, description="Enable or disable Hindsight institutional memory")


class ResetMemoryResponse(BaseModel):
    success: bool
    message: str


@app.get("/")
def serve_index():
    """Serve the single-page frontend application."""
    if INDEX_FILE.exists():
        return FileResponse(INDEX_FILE, media_type="text/html")
    return HTMLResponse("<h1>WhyDesk Frontend not found</h1>", status_code=404)


@app.get("/api/health")
def get_health():
    """Verify backend, Hindsight cloud reachability, and Groq status."""
    hindsight_ok = False
    bank_ready = False
    groq_ok = False

    # Check Hindsight
    if memory.backend_type == "Hindsight Cloud" and memory.client:
        try:
            mems = memory.list_memories()
            hindsight_ok = True
            bank_ready = True
        except Exception:
            hindsight_ok = False
    else:
        # Local simulation is ready
        hindsight_ok = True
        bank_ready = True

    # Check Groq
    if agent.groq_client:
        groq_ok = True
    else:
        groq_ok = False

    return {
        "status": "healthy",
        "hindsight_reachable": hindsight_ok,
        "groq_reachable": groq_ok,
        "bank_ready": bank_ready,
        "active_memory_backend": memory.backend_type,
        "bank_id": memory.bank_id,
        "groq_model": config.GROQ_MODEL,
    }


@app.post("/api/investigate")
def investigate_endpoint(req: InvestigateRequest):
    """Run full investigation workflow."""
    try:
        result = agent.investigate(
            question=req.question,
            stakeholder=req.stakeholder,
            use_memory=req.use_memory,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Investigation failed: {str(e)}")


@app.get("/api/memories")
def get_memories():
    """Retrieve all institutional memories currently stored in the bank."""
    try:
        items = memory.list_memories()
        return {
            "total": len(items),
            "memories": items,
            "bank_id": memory.bank_id,
            "backend_type": memory.backend_type,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list memories: {str(e)}")


@app.post("/api/reset-memory", response_model=ResetMemoryResponse)
def reset_memory_endpoint():
    """Reset the institutional memory bank to clean state."""
    try:
        memory.reset_bank()
        return ResetMemoryResponse(
            success=True,
            message="Memory bank reset successfully.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset memory: {str(e)}")


@app.post("/api/seed-demo")
def seed_demo_endpoint():
    """Replay demo Runs 1 to 4 through the live pipeline on a fresh bank."""
    try:
        memory.reset_bank()

        demo_runs = [
            {
                "run": 1,
                "stakeholder": "Finance Head",
                "question": "Why did revenue drop 18% in the South region in W10, and FYI I only ever want a 1-line summary with the exact dollar impact.",
                "use_memory": True,
            },
            {
                "run": 2,
                "stakeholder": "Senior Analyst",
                "question": "Alert says Monday revenue in W11 is down 64% across South. Did pricing break again?",
                "use_memory": True,
            },
            {
                "run": 3,
                "stakeholder": "Senior Analyst",
                "question": "North hardware bundle revenue dipped 24% in W11. Sales blames a competitor promo or holiday. True?",
                "use_memory": True,
            },
            {
                "run": 4,
                "stakeholder": "Senior Analyst",
                "question": "South region revenue dropped 15% again in W12. Investigate.",
                "use_memory": True,
            },
        ]

        results = []
        for d in demo_runs:
            res = agent.investigate(
                question=d["question"],
                stakeholder=d["stakeholder"],
                use_memory=d["use_memory"],
            )
            results.append(
                {
                    "run": d["run"],
                    "question": d["question"],
                    "stakeholder": d["stakeholder"],
                    "answer": res["answer"],
                    "tool_count": len(res["tool_trace"]),
                    "skipped_count": len(res["skipped_tools"]),
                }
            )

        return {
            "success": True,
            "seeded_runs": len(results),
            "runs": results,
            "total_memories": len(memory.list_memories()),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to seed demo history: {str(e)}")

