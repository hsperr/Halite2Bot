import subprocess
import re
import multiprocessing
import json
import time
import dlib


class Worker(multiprocessing.Process):
    def __init__(self, task_queue, result_queue):
        multiprocessing.Process.__init__(self)
        self._task_queue = task_queue
        self._result_queue = result_queue

    def run(self):
        while True:
            weights, seed = self._task_queue.get()
            if weights is None:
                break

            wins = self.run_experiment(weights, seed)
            result_queue.put(wins)

    def run_experiment(self, weights, seed):
            args = ['/Users/Henning/Downloads/Halite-II/environment/halite', '-r', '-q', '-s', str(seed), '-d', '240 160', 'python3 Vectorian.py '+'#'.join([str(x) for x in weights]), 'python3 TheDorianV6.2.norush.py']
            results = json.loads(subprocess.check_output(args).decode('utf-8'))
            return results['stats']['0']['rank'] == 1


result_queue = multiprocessing.JoinableQueue(1000)
task_queue = multiprocessing.JoinableQueue(1000)
NUM_WORKERS=8

for i in range(NUM_WORKERS):
    worker = Worker(task_queue, result_queue)
    worker.start()


import random
random.seed(43388)
n = 9
runs = 50
seeds = [int(''.join(["%s" % random.randint(0, 9) for num in range(0, n)])) for i in range(runs)]
print("example seed", seeds[:2])

def minimizable(weights):
    results= []
    t0 = time.time()
    for i, seed in zip(range(runs), seeds):
        task_queue.put((weights, seed))

    while not len(results)==runs:
        results.append(result_queue.get())
        if len(results)%10==0:
            print(weights, sum(results), len(results), 'w/r', sum(results)/len(results))

    print(weights, sum(results)/len(results), (time.time()-t0)/len(results))
    return -sum(results)/len(results)

starting_values = [0.02, 0.01, 0.05, 0.1, 0.01]
bounds = [(0.00001, 0.9)] * len(starting_values)

# Find the optimal inputs to holder_table().  The print statements that follow
# show that find_min_global() finds the optimal settings to high precision.
print(dlib.find_min_global(minimizable, 
                           [x[0] for x in bounds],  # Lower bound constraints on x0 and x1 respectively
                           [x[1] for x in bounds],    # Upper bound constraints on x0 and x1 respectively
                           80))         # The number of times find_min_global() will call holder_table()
