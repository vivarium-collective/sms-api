import multiprocessing as mp
from typing import Any
import numpy as np

from api.data_model.vivarium import VivariumDocument
from api.gateway.handlers.vivarium import run_vivarium


def collect(queue: mp.Queue, channel: list, thread_id: str):
    """Collect results asynchronously"""
    while True:
        try:
            val = queue.get(timeout=0.1)
            channel.append(val)
        except:
            break  # assume done if empty after timeout


def launch_scan(
    document: VivariumDocument, 
    duration: float, 
    n_threads: int, 
    perturbation_config: dict[str, Any] | None = None,
    distribution_config: dict[str, Any] | None = None
):
    def worker(thread_id: str, q: mp.Queue):
        # for t in range(duration):  # type: ignore
        #     result = func(t)
        #     q.put(result)
        result = run_vivarium(document, duration)
        q.put(result)
    
    # launch processes
    processes = []
    queues = {str(i): mp.Queue() for i in range(n_threads)}  # inter-process
    channels = {str(i): [] for i in range(n_threads)}  # final output

    for i in range(n_threads):
        thread_id = str(i)
        p = mp.Process(target=worker, args=(thread_id, queues[thread_id]))
        p.start()
        processes.append(p)

    # collect results
    for i in range(n_threads):
        collect(queues[str(i)], channels[str(i)], str(i))

    # join processes
    for p in processes:
        p.join()

    # extract data
    results = {}
    for tid, data in channels.items():
        print(f"Thread {tid} channel:", data)
        results[tid] = data
    
    return results
