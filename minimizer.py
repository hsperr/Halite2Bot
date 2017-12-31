import subprocess
import re
import multiprocessing

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
            args = ['./halite', '-s', str(seed), '-d', '240 160', 'python3 Vectorian.py '+'#'.join([str(x) for x in weights]), 'python3 sentdexbot.py']
            line = subprocess.check_output(args).decode('utf-8').split('\n')[-3]
            assert "Player #0" in line

            frame = re.search('frame #(\d*)', line, re.IGNORECASE)
            frame = int(frame.group(1))

            ships = re.search('(\d*) ships', line, re.IGNORECASE)
            ships = int(ships.group(1))

            rank = re.search('rank #(\d)', line, re.IGNORECASE)
            rank = int(rank.group(1))
            
            wins = 0
            if rank == 1:
                wins+=1
            #print(runs, [line.split(',')[:2], frame, ships, rank], wins)
            return wins


from scipy.optimize import minimize

result_queue = multiprocessing.JoinableQueue(1000)
task_queue = multiprocessing.JoinableQueue(1000)
NUM_WORKERS=8

for i in range(NUM_WORKERS):
    worker = Worker(task_queue, result_queue)
    worker.start()

starting_values = [0.001, 0.001, 0.002, 0.02, 0.02]
bounds = [(0.00001, 0.9)] * len(starting_values)

import random
random.seed(433)
n = 9
runs = 8
seeds = [int(''.join(["%s" % random.randint(0, 9) for num in range(0, n)])) for i in range(runs)]
print("example seed", seeds[:2])

import time
def minimizable(weights):
    print(weights, "starting")
    results= []
    for i, seed in zip(range(runs), seeds):
        task_queue.put((weights, seed))

    while not len(results)==runs:
        results.append(result_queue.get())
        if len(results)%10==0:
            print(weights, sum(results), len(results), 'w/r', sum(results)/len(results))

    print(weights, sum(results)/len(results))
    return -sum(results)/len(results)

options = {'disp': None, 'maxls': 20, 'iprint': -1, 'gtol': 1e-04, 'eps': 1e-03, 'maxiter': 15000, 'ftol': 2.220446049250313e-09, 'maxcor': 10, 'maxfun': 15000}
print(minimize(minimizable, starting_values, method='L-BFGS-B', bounds=bounds, options=options))
