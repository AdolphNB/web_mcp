"""Outbound HTTPS polling; the visitor never connects to the owner's PC."""
from concurrent.futures import ThreadPoolExecutor
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger("website-support")


def run_agent(job, config):
    safe_env = {k: v for k, v in os.environ.items() if k.upper() in {
        "PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "LOCALAPPDATA", "APPDATA", "TEMP", "TMP", "USERPROFILE", "HOME"}}
    safe_env.update(HERMES_HOME=config["profile"], PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    result = subprocess.run([config["hermes_python"], str(Path(__file__).with_name("support_agent.py"))],
        input=json.dumps(job), encoding="utf-8", capture_output=True, timeout=100,
        cwd=config["profile"], env=safe_env,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    for line in reversed(result.stdout.splitlines()):
        if line.startswith("SUPPORT_RESULT="):
            return json.loads(line.split("=", 1)[1])
    # Never copy provider errors or raw agent logs into a visitor reply.
    return {"success": False, "answer": ""}


def main(config_file):
    config = json.loads(Path(config_file).read_text(encoding="utf-8"))
    base = config["site_url"].rstrip("/")
    parsed = urlsplit(base)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        raise ValueError("Use the HTTPS site origin")
    token = Path(config["token_file"]).read_text(encoding="utf-8").strip()
    if len(token) < 32:
        raise ValueError("Configure a dedicated support-worker token")
    with httpx.Client(base_url=base, headers={"Authorization": "Bearer " + token}, timeout=15, follow_redirects=False) as client, ThreadPoolExecutor(max_workers=1) as pool:
        while True:
            try:
                response = client.post("/api/support/worker/claim")
                response.raise_for_status()
                job = response.json().get("job")
                if not job:
                    time.sleep(5)
                    continue
                logger.info("Processing support question")
                future = pool.submit(run_agent, job, config)
                while not future.done():
                    time.sleep(10)
                    try:
                        client.post("/api/support/worker/heartbeat").raise_for_status()
                    except httpx.HTTPError:
                        logger.warning("Heartbeat unavailable")
                try:
                    result = future.result()
                except Exception:
                    result = {"success": False, "answer": ""}
                for attempt in range(3):
                    try:
                        delivered = client.post(f"/api/support/worker/{job['id']}/complete", json={**result, "lease": job["lease"]})
                        delivered.raise_for_status()
                        break
                    except httpx.HTTPError:
                        if attempt == 2:
                            raise
                        time.sleep(2)
                logger.info("Question completed: %s", "answered" if result["success"] else "fallback")
            except Exception as exc:
                logger.warning("Worker retry (%s)", type(exc).__name__)
                time.sleep(10)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    main(sys.argv[1])
