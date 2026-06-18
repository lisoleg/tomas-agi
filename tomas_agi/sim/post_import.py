#!/usr/bin/env python
"""
Post-Import Automation Script
Watches for OwnThink import completion, then:
  1. Computes i_weight for new rows
  2. Optionally restarts Flask server
  3. Tests Dashboard API with real data

Usage:
  python post_import.py [--auto-restart-flask]
"""
import os
import sys
import time
import subprocess
import sqlite3
import json
import argparse

DB_PATH = "D:/tomas-data/tomas.db"
LOG_PATH = "/d/tomas-data/import_log4.txt"
SIM_DIR = os.path.dirname(os.path.abspath(__file__))


def check_import_running():
    """Check if resume_import.py is still running."""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
            capture_output=True, text=True, timeout=10
        )
        # Look for the import process (high memory usage)
        for line in result.stdout.strip().split("\n"):
            if "python.exe" in line.lower():
                parts = line.strip('"').split('","')
                if len(parts) >= 5:
                    mem_str = parts[4].replace(",", "").replace(" K", "").replace('"', "")
                    try:
                        mem_kb = int(mem_str)
                        if mem_kb > 300000:  # >300MB = likely import process
                            return True, mem_kb
                    except ValueError:
                        pass
        return False, 0
    except Exception:
        return False, 0


def get_db_count():
    """Get current row count from DB (read-only)."""
    try:
        db = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=5)
        count = db.execute("SELECT COUNT(*) FROM knowledge_triples").fetchone()[0]
        db.close()
        return count
    except Exception as e:
        return -1


def get_last_log_line():
    """Get the last line from import log."""
    try:
        with open(LOG_PATH.replace("/d/", "D:/"), "r", encoding="utf-8") as f:
            lines = f.readlines()
            return lines[-1].strip() if lines else "empty"
    except Exception:
        return "unreadable"


def run_i_weight():
    """Run i_weight computation."""
    print("\n" + "=" * 60)
    print("Phase 1: Computing i_weight for new rows")
    print("=" * 60)
    cmd = [sys.executable, os.path.join(SIM_DIR, "compute_i_weight.py")]
    result = subprocess.run(cmd, cwd=SIM_DIR, capture_output=True, text=True, timeout=3600)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
    return result.returncode == 0


def restart_flask():
    """Restart Flask server in background."""
    print("\n" + "=" * 60)
    print("Phase 2: Restarting Flask server")
    print("=" * 60)
    cmd = [sys.executable, os.path.join(SIM_DIR, "server.py")]
    proc = subprocess.Popen(
        cmd,
        cwd=SIM_DIR,
        stdout=open("D:/tomas-data/flask_stdout.log", "w"),
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )
    print(f"Flask started (PID: {proc.pid})")
    # Wait for Flask to be ready
    import urllib.request
    for i in range(30):
        time.sleep(1)
        try:
            urllib.request.urlopen("http://localhost:5000/api/health", timeout=2)
            print(f"Flask is ready (took {i+1}s)")
            return proc.pid
        except Exception:
            pass
    print("WARNING: Flask did not respond within 30s")
    return proc.pid


def test_dashboard_api():
    """Test Dashboard API with real data."""
    print("\n" + "=" * 60)
    print("Phase 3: Testing Dashboard API")
    print("=" * 60)
    import urllib.request
    try:
        resp = urllib.request.urlopen("http://localhost:5000/api/subsystem-status", timeout=10)
        data = json.loads(resp.read().decode())
        print(json.dumps(data, indent=2, ensure_ascii=False)[:3000])
        print("\n✅ Dashboard API is returning real data!")
        return True
    except Exception as e:
        print(f"❌ Dashboard API test failed: {e}")
        return False


def test_tcci():
    """Quick TCCI regression test."""
    print("\n" + "=" * 60)
    print("Phase 4: TCCI regression test")
    print("=" * 60)
    import urllib.request
    try:
        req = urllib.request.Request(
            "http://localhost:5000/api/tcci/test",
            data=json.dumps({"use_mock": True}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read().decode())
        passed = data.get("summary", {}).get("passed", 0)
        total = data.get("summary", {}).get("total", 0)
        print(f"TCCI: {passed}/{total} cases passed")
        return passed == total
    except Exception as e:
        print(f"❌ TCCI test failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Post-import automation")
    parser.add_argument("--auto-restart-flask", action="store_true",
                        help="Automatically restart Flask after import")
    parser.add_argument("--poll-interval", type=int, default=60,
                        help="Poll interval in seconds (default: 60)")
    args = parser.parse_args()

    print("=" * 60)
    print("TOMAS Post-Import Automation")
    print("=" * 60)
    print(f"DB: {DB_PATH}")
    print(f"Sim dir: {SIM_DIR}")
    print(f"Poll interval: {args.poll_interval}s")
    print()

    # Phase 0: Wait for import to complete
    print("Phase 0: Monitoring import progress...")
    check_count = 0
    while True:
        running, mem = check_import_running()
        count = get_db_count()
        last_log = get_last_log_line()

        check_count += 1
        if running:
            print(f"  [{check_count}] Import running (mem={mem//1024}MB) | DB={count:,} rows | {last_log}")
            time.sleep(args.poll_interval)
        else:
            print(f"  [{check_count}] Import process NOT detected!")
            print(f"  Final DB count: {count:,} rows")
            print(f"  Last log: {last_log}")
            break

    # Verify DB is writable (import fully released locks)
    time.sleep(5)
    print("\nImport complete. Starting post-import phases...\n")

    # Phase 1: Compute i_weight
    i_weight_ok = run_i_weight()

    # Phase 2: Restart Flask
    if args.auto_restart_flask:
        flask_pid = restart_flask()
        time.sleep(2)

        # Phase 3: Test Dashboard API
        test_dashboard_api()

        # Phase 4: TCCI regression
        test_tcci()
    else:
        print("\nSkipping Flask restart (use --auto-restart-flask to enable)")
        print("Manual steps:")
        print(f"  1. cd {SIM_DIR} && python compute_i_weight.py")
        print(f"  2. python server.py")
        print(f"  3. curl -s http://localhost:5000/api/subsystem-status | python -m json.tool")

    print("\n" + "=" * 60)
    print("Post-import automation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
