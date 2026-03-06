import asyncio
import os
import time
import shutil
from pathlib import Path
from backend.app.core.config import settings
from backend.app.services.watcher import start_watcher, stop_watcher

async def monitor_loop_lag():
    lags = []
    while True:
        start = time.perf_counter()
        await asyncio.sleep(0.01)
        end = time.perf_counter()
        lag = end - start - 0.01
        lags.append(lag)
        if len(lags) > 100:
            lags.pop(0)
        # print(f"Loop lag: {lag:.6f}s")
        await asyncio.sleep(0.1)

async def main():
    # Setup watch directory
    watch_dir = settings.WATCH_DIR
    if os.path.exists(watch_dir):
        shutil.rmtree(watch_dir)
    os.makedirs(watch_dir)

    print(f"Monitoring {watch_dir}")

    # Start the watcher
    start_watcher()

    # Start lag monitor
    lag_task = asyncio.create_task(monitor_loop_lag())

    # Create some files to trigger ingestion
    num_files = 5
    file_size_mb = 10 # 10MB each

    print(f"Creating {num_files} files of {file_size_mb}MB each...")

    start_time = time.time()

    for i in range(num_files):
        file_path = os.path.join(watch_dir, f"test_file_{i}.txt")
        with open(file_path, "wb") as f:
            f.write(os.urandom(file_size_mb * 1024 * 1024))
        print(f"Created {file_path}")
        await asyncio.sleep(0.5) # Space them out a bit

    print("Waiting for ingestion to complete...")
    # The watcher has a 2 second sleep, plus processing time.
    # We'll wait until all .processed files are created or timeout.

    timeout = 30
    start_wait = time.time()
    while time.time() - start_wait < timeout:
        processed_files = [f for f in os.listdir(watch_dir) if f.endswith(".processed")]
        if len(processed_files) == num_files:
            break
        await asyncio.sleep(1)

    end_time = time.time()
    print(f"Ingestion took {end_time - start_time:.2f} seconds")

    lag_task.cancel()
    stop_watcher()

    # Check for markers
    processed_files = [f for f in os.listdir(watch_dir) if f.endswith(".processed")]
    print(f"Processed files: {len(processed_files)}/{num_files}")

if __name__ == "__main__":
    # We need a running loop for start_watcher
    asyncio.run(main())
