"""
Simple Worker module. This module should do the following:

1. connect to the db on startup
2. poll for new jobs
3. for each new jobi:
3a.   spawn new process(jobi)
3b.   run job(jobi)
3c.   save job results to db(jobi.results)
"""


import asyncio
from concurrent.futures import ProcessPoolExecutor
from time import sleep
import random

jobs = iter([random.randint(1000, 9999) for _ in range(5)])


# this func should run the job and save it to db
def run(job_id: int) -> None:
    print(f"Processing job {job_id}")
    sleep(random.uniform(1, 3))  # Replace with real simulation
    print(f"Finished job {job_id}")


# this func should poll jobs and return new ones
async def poll_for_jobs() -> int:
    try:
        return next(jobs)
    except:
        print('No more jobs')
        raise RuntimeError('Done.')


# this func should be the worker loop
async def worker_loop(pool: ProcessPoolExecutor) -> None:
    seen = set()
    while True:
        try:
            job = await poll_for_jobs()
            if job and job not in seen:
                seen.add(job)
                loop = asyncio.get_running_loop()
                loop.run_in_executor(pool, run, job)
                print(f'Finished: {job}')
            for i in range(4):
                print(f'Sleep {i} for job: {job}')
                await asyncio.sleep(0.5)
        except RuntimeError:
            print('There are no more jobs. Done. Waiting.')


# this func should spin up a new process worker for each request
async def main() -> None:
    with ProcessPoolExecutor(max_workers=4) as pool:
        await worker_loop(pool)


if __name__ == "__main__":
    asyncio.run(main())