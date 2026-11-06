"""Capture high-fidelity screenshots of WhyDesk with live investigation results."""

import json
import urllib.request
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def capture_screenshots():
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    tmp_profile = r"C:\Users\shrid\AppData\Local\Temp\cdir_live_demo"

    # Fetch live Run 5 results from backend
    req = urllib.request.Request(
        "http://localhost:8000/api/investigate",
        headers={"Content-Type": "application/json"},
        data=json.dumps({
            "question": "Why did revenue drop 19% in the South region in W13?",
            "stakeholder": "Finance Head",
            "use_memory": True,
        }).encode(),
    )
    res = urllib.request.urlopen(req)
    data = json.loads(res.read().decode())
    print("Live Run 5 fetched:", len(data["tool_trace"]), "tools run,", len(data["skipped_tools"]), "skipped.")

    # Read base index.html
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    # Inject pre-rendered state so headless Chrome renders immediately without async delays
    injection = f"""
    <script>
      window.addEventListener('DOMContentLoaded', () => {{
        const liveData = {json.dumps(data)};
        const welcome = document.getElementById('welcomeCard');
        if (welcome) welcome.remove();
        renderInvestigationResult(liveData);
        updateInspector(liveData);
        setStatus('Investigation complete (' + liveData.timings.total_ms + 'ms)');
      }});
    </script>
    """
    rendered_html = index_html.replace("</body>", f"{injection}\n</body>")

    render_file = ROOT / "frontend" / "live_snapshot.html"
    render_file.write_text(rendered_html, encoding="utf-8")

    # 1. 1920x1080 screenshot
    shot_1920 = ROOT / "screenshot_1920x1080.png"
    cmd_1920 = [
        chrome_path,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        f"--user-data-dir={tmp_profile}_1920",
        "--window-size=1920,1080",
        f"--screenshot={shot_1920}",
        f"file:///{render_file.as_posix()}",
    ]
    print("Capturing 1920x1080 screenshot...")
    subprocess.run(cmd_1920, check=True)

    # 2. 1440x900 screenshot
    shot_1440 = ROOT / "screenshot_1440x900.png"
    cmd_1440 = [
        chrome_path,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        f"--user-data-dir={tmp_profile}_1440",
        "--window-size=1440,900",
        f"--screenshot={shot_1440}",
        f"file:///{render_file.as_posix()}",
    ]
    print("Capturing 1440x900 screenshot...")
    subprocess.run(cmd_1440, check=True)

    # Clean up temp snapshot file
    if render_file.exists():
        render_file.unlink()

    print("Live screenshots captured successfully.")


if __name__ == "__main__":
    capture_screenshots()
