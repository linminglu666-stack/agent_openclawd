import asyncio
import os
import signal
import subprocess
import sys
import threading
from typing import List

# Config
SERVICES = [
    "code/services/scheduler_service.py",
    "code/services/orchestrator_service.py",
    "code/services/runner_service.py",
    "code/services/growth_loop_service.py",
]

class ProcessManager:
    def __init__(self):
        self.procs: List[subprocess.Popen] = []
        self.shutdown_event = threading.Event()

    def start_all(self):
        env = os.environ.copy()
        # Ensure PYTHONPATH includes current directory so imports work
        cwd = os.getcwd()
        if "PYTHONPATH" not in env:
            env["PYTHONPATH"] = cwd
        else:
            env["PYTHONPATH"] = f"{cwd}:{env['PYTHONPATH']}"

        print(f"[OpenClawd] Starting {len(SERVICES)} services...")
        for script in SERVICES:
            cmd = [sys.executable, script]
            # We let them inherit stdout/stderr so they print to console
            # In a real supervisor we might redirect them.
            # Here, openclawd's stdout is the aggregation.
            p = subprocess.Popen(cmd, env=env, stdout=sys.stdout, stderr=sys.stderr, cwd=cwd)
            self.procs.append(p)
            print(f"[OpenClawd] Started {script} (PID: {p.pid})")

    def stop_all(self):
        print("[OpenClawd] Stopping all services...")
        self.shutdown_event.set()
        for p in self.procs:
            if p.poll() is None:
                p.terminate()
        
        # Wait a bit
        for p in self.procs:
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()
        print("[OpenClawd] All services stopped.")

    def monitor(self):
        try:
            while not self.shutdown_event.is_set():
                # Check if any died
                all_dead = True
                for p in self.procs:
                    if p.poll() is None:
                        all_dead = False
                    else:
                        # Restart? For now, just log.
                        # print(f"[OpenClawd] Process {p.pid} exited with {p.returncode}")
                        pass
                
                if all_dead and self.procs:
                    print("[OpenClawd] All processes died. Exiting.")
                    break
                
                asyncio.run(asyncio.sleep(1))
        except KeyboardInterrupt:
            self.stop_all()

def main():
    pm = ProcessManager()
    
    def handle_sig(signum, frame):
        pm.stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)

    pm.start_all()
    pm.monitor()

if __name__ == "__main__":
    main()
