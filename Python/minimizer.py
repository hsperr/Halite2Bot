import subprocess
import re
import multiprocessing
import json
import time

from scipy.optimize import minimize

class Worker(multiprocessing.Process):
    def __init__(self, task_queue, result_queue):
        multiprocessing.Process.__init__(self)
        self._task_queue = task_queue
        self._result_queue = result_queue

    def run(self):
        while True:
            map_size, seed, bots = self._task_queue.get()
            if not map_size:
                break

            wins = self.run_experiment(map_size, seed, bots)
            result_queue.put(wins)

    def run_experiment(self, map_size, seed, bots):
        args = ['/Users/Henning/Downloads/Halite-II/environment/halite', '-r', '-q', '-s', str(seed), '-d', map_size]
        for bot, botargs in bots:
            args.append('python3 {} {}'.format(bot, botargs).strip())

        results = json.loads(subprocess.check_output(args).decode('utf-8'))
        return results['stats']['0']['rank'] == 1


result_queue = multiprocessing.JoinableQueue(1000)
task_queue = multiprocessing.JoinableQueue(1000)
NUM_WORKERS=8

for i in range(NUM_WORKERS):
    worker = Worker(task_queue, result_queue)
    worker.start()

starting_values = [0.01, 0.005, 0.01, 3, 0.001]
bounds = [(0.0001, 10)] * len(starting_values)

import random
random.seed(433111)

n = 9
runs = 60

map_sizes = [240, 264, 288, 312, 336, 360, 384]

seeds = [int(''.join(["%s" % random.randint(0, 9) for num in range(0, n)])) for i in range(runs)]
maps = [random.choice(map_sizes) for x in range(runs)]
maps = ["{} {}".format(x, int(x/1.5)) for x in maps]

print("example seed", seeds[:2])

def minimizable(weights):
    results= []
    t0 = time.time()

    contestant = ("Vectorian.fixmexican.py", '#'.join([str(x) for x in weights]))
    for i, mapsize, seed in zip(range(runs), maps, seeds):
        if i < runs/4:
            bots = [
                contestant,
                ("Vectorian.submitted.py", ''),
            ]
        else:
            bots = [
                contestant,
                ("TheDorianV6.2.submitted.better.collisions.py", ''),
            ]
#       else:
#           bots = [
#               contestant,
#               ("Vectorian.submitted.py", ''),
#               ("TheDorianV6.2.submitted.better.collisions.py", ''),
#               ("TheDorianV6.2.submitted.better.collisions.py", ''),
#           ]

        task_queue.put((mapsize, seed, bots))

    while not len(results)==runs:
        results.append(result_queue.get())
        if len(results)%10==0:
            print(weights, sum(results), len(results), 'w/r', sum(results)/len(results), 'total w/r', sum(results)/runs)
    print(weights, sum(results)/len(results), 'time', round((time.time()-t0)/len(results), 2))
    return -sum(results)/len(results)

options = {'disp': None, 'maxls': 20, 'iprint': -1, 'gtol': 1e-04, 'eps': 1e-02, 'maxiter': 15000, 'ftol': 2.220446049250313e-09, 'maxcor': 10, 'maxfun': 15000}
print(minimize(minimizable, starting_values, method='L-BFGS-B', bounds=bounds, options=options))
#print(minimize(minimizable, starting_values, method='Powell', bounds=bounds, options=options))
