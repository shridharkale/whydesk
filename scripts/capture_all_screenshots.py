"""Automated capture of all required WhyDesk screenshots per Section 5 Task 5."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.agent import WhyDeskAgent
from backend.memory import WhyDeskMemory

CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
OUT_DIR = ROOT / "docs" / "screenshots"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def take_screenshot(html_path: Path, out_path: Path, width: int, height: int):
    cmd = [
        CHROME_BIN,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        f"--user-data-dir=/tmp/whydesk_shot_{width}x{height}",
        f"--window-size={width},{height}",
        f"--screenshot={out_path}",
        f"file://{html_path.resolve()}",
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        print(f"Error capturing {out_path.name}: {res.stderr.decode()}")
    else:
        print(f"Captured: {out_path.name} ({width}x{height})")


def main():
    base_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    # -------------------------------------------------------------
    # 1. Empty State
    # -------------------------------------------------------------
    empty_html_path = ROOT / "frontend" / "temp_empty.html"
    empty_html_path.write_text(base_html, encoding="utf-8")

    take_screenshot(empty_html_path, OUT_DIR / "empty_state_1920x1080.png", 1920, 1080)
    take_screenshot(empty_html_path, OUT_DIR / "empty_state_1440x900.png", 1440, 900)
    if empty_html_path.exists():
        empty_html_path.unlink()

    # -------------------------------------------------------------
    # Execute Runs 1-4 and Run 5 on Agent
    # -------------------------------------------------------------
    memory = WhyDeskMemory()
    memory.reset_bank()
    agent = WhyDeskAgent(memory=memory)

    # Seed runs 1 to 4
    agent.investigate("Why did revenue drop 18% in the South region in W10, and FYI I only ever want a 1-line summary with the exact dollar impact.", "Finance Head", True)
    agent.investigate("Alert says Monday revenue in W11 is down 64% across South. Did pricing break again?", "Senior Analyst", True)
    agent.investigate("North hardware bundle revenue dipped 24% in W11. Sales blames a competitor promo or holiday. True?", "Senior Analyst", True)
    agent.investigate("South region revenue dropped 15% again in W12. Investigate.", "Senior Analyst", True)

    # Run 5 Memory ON
    run5_on = agent.investigate(
        question="Why did revenue drop 19% in the South region in W13?",
        stakeholder="Finance Head",
        use_memory=True,
    )

    # Run 5 Memory OFF
    run5_off = agent.investigate(
        question="Why did revenue drop 19% in the South region in W13?",
        stakeholder="Finance Head",
        use_memory=False,
    )

    # -------------------------------------------------------------
    # 2. Run 5 with Memory ON (Trace Table & Inspector Visible)
    # -------------------------------------------------------------
    run5_script = f"""
    <script>
      window.addEventListener('DOMContentLoaded', () => {{
        const liveData = {json.dumps(run5_on)};
        const empty = document.getElementById('emptyChatState');
        if (empty) empty.remove();
        renderInvestigationResult(liveData, "Why did revenue drop 19% in the South region in W13?");
        updateInspector(liveData);
        setStatus("Complete (" + liveData.timings.total_ms + "ms)");
      }});
    </script>
    """
    run5_html_path = ROOT / "frontend" / "temp_run5.html"
    run5_html_path.write_text(base_html.replace("</body>", f"{run5_script}\n</body>"), encoding="utf-8")

    take_screenshot(run5_html_path, OUT_DIR / "run5_memory_on_1920x1080.png", 1920, 1080)
    take_screenshot(run5_html_path, OUT_DIR / "run5_memory_on_1440x900.png", 1440, 900)
    if run5_html_path.exists():
        run5_html_path.unlink()

    # -------------------------------------------------------------
    # 3. Memory ON vs OFF Comparison View
    # -------------------------------------------------------------
    compare_script = f"""
    <script>
      window.addEventListener('DOMContentLoaded', () => {{
        const empty = document.getElementById('emptyChatState');
        if (empty) empty.remove();

        const resOn = {json.dumps(run5_on)};
        const resOff = {json.dumps(run5_off)};
        const question = "Why did revenue drop 19% in the South region in W13?";

        const chatScroll = document.getElementById("chatScroll");
        const compCard = document.createElement("div");
        compCard.className = "compare-card";

        const header = document.createElement("div");
        header.className = "compare-header";
        header.innerHTML = `
          <span class="query-heading">Comparison: "${{question}}"</span>
          <span class="status-text">Finance Head</span>
        `;
        compCard.appendChild(header);

        const grid = document.createElement("div");
        grid.className = "compare-grid";
        grid.innerHTML = `
          <div class="compare-pane">
            <div class="compare-pane-title">
              <span>Memory on</span>
              <span class="compare-meta-stat">${{resOn.tool_trace.length}} tools • ${{resOn.timings.total_ms}}ms</span>
            </div>
            <div class="trace-summary-line">${{resOn.checks_summary}}</div>
            <div class="answer-box" style="margin-top: 4px;">
              <div class="answer-label">${{resOn.stakeholder_format_used}}</div>
              <div class="answer-text">${{resOn.answer}}</div>
            </div>
          </div>

          <div class="compare-pane">
            <div class="compare-pane-title">
              <span>Memory off</span>
              <span class="compare-meta-stat">${{resOff.tool_trace.length}} tools • ${{resOff.timings.total_ms}}ms</span>
            </div>
            <div class="trace-summary-line">${{resOff.checks_summary}}</div>
            <div class="answer-box-plain" style="margin-top: 4px;">
              <div class="answer-label-muted">${{resOff.stakeholder_format_used}}</div>
              <div class="answer-text">${{resOff.answer}}</div>
            </div>
          </div>
        `;
        compCard.appendChild(grid);
        chatScroll.appendChild(compCard);
        updateInspector(resOn);
        setStatus("Comparison complete.");
      }});
    </script>
    """
    compare_html_path = ROOT / "frontend" / "temp_compare.html"
    compare_html_path.write_text(base_html.replace("</body>", f"{compare_script}\n</body>"), encoding="utf-8")

    take_screenshot(compare_html_path, OUT_DIR / "compare_view_1920x1080.png", 1920, 1080)
    take_screenshot(compare_html_path, OUT_DIR / "compare_view_1440x900.png", 1440, 900)
    if compare_html_path.exists():
        compare_html_path.unlink()

    print("\nAll 6 screenshots captured successfully in docs/screenshots/")


if __name__ == "__main__":
    main()
