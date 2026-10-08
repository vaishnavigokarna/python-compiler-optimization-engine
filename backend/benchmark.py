import subprocess
import sys
import tempfile
import time
import textwrap

def benchmark_code(source: str, runs: int = 3, timeout_seconds: float = 5.0):
    runs = max(1, min(int(runs), 5))
    times = []
    outputs = []
    errors = []

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(source)
        path = f.name

    try:
        for _ in range(runs):
            start = time.perf_counter()
            try:
                proc = subprocess.run(
                    [sys.executable, path],
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )
                elapsed = time.perf_counter() - start
                times.append(elapsed)
                outputs.append(proc.stdout)
                errors.append(proc.stderr)
                if proc.returncode != 0:
                    return {
                        "success": False,
                        "error": proc.stderr or f"Process exited with code {proc.returncode}",
                        "times": times,
                    }
            except subprocess.TimeoutExpired:
                return {"success": False, "error": "Execution timed out.", "times": times}
    finally:
        try:
            import os
            os.remove(path)
        except OSError:
            pass

    avg = sum(times) / len(times)
    return {
        "success": True,
        "average_time": avg,
        "min_time": min(times),
        "max_time": max(times),
        "output": outputs[-1],
        "stderr": errors[-1],
        "runs": len(times),
    }

def compare(original: str, optimized: str, runs: int = 3):
    a = benchmark_code(original, runs=runs)
    if not a["success"]:
        return {"success": False, "original": a, "optimized": None, "same_output": False}

    b = benchmark_code(optimized, runs=runs)
    if not b["success"]:
        return {"success": False, "original": a, "optimized": b, "same_output": False}

    same = a["output"] == b["output"]
    improvement = None
    if a["average_time"] > 0:
        improvement = (a["average_time"] - b["average_time"]) / a["average_time"] * 100

    return {
        "success": True,
        "same_output": same,
        "original": a,
        "optimized": b,
        "improvement_percent": improvement,
    }
