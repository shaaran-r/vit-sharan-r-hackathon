import os
import subprocess
import sys
import time

import requests


def main() -> int:
    api = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.main:app", "--host", "127.0.0.1", "--port", "8000"],
        env=os.environ.copy(),
    )
    try:
        for _ in range(30):
            if api.poll() is not None:
                raise RuntimeError("API server exited before becoming ready")
            try:
                response = requests.get("http://127.0.0.1:8000/health", timeout=1)
                response.raise_for_status()
                break
            except requests.RequestException:
                time.sleep(1)
        else:
            raise RuntimeError("Timed out waiting for the API server")

        print("API ready at http://localhost:8000; opening dashboard at http://localhost:8501")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "src/dashboard/app.py",
                "--server.headless=true",
                "--browser.gatherUsageStats=false",
                "--server.address=127.0.0.1",
                "--server.port=8501",
            ],
            check=False,
            env=os.environ.copy(),
        )
    except KeyboardInterrupt:
        pass
    finally:
        api.terminate()
        try:
            api.wait(timeout=5)
        except subprocess.TimeoutExpired:
            api.kill()
            api.wait()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
