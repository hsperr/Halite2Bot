import subprocess
import re
import json
import multiprocessing

class Worker(multiprocessing.Process):
    def __init__(self, task_queue, result_queue):
        multiprocessing.Process.__init__(self)
        self._task_queue = task_queue
        self._result_queue = result_queue

    def run(self):
        while True:
            bots = self._task_queue.get()
            if bots is None:
                break

            bot1, bot2, seed = bots

            wins = self.run_experiment(bot1, bot2, seed)
            result_queue.put(wins)

    def run_experiment(self, bot1, bot2, seed):
            args = ['./halite', '-r' ,'-q', '-s', str(seed), '-d', '240 160', 'python3 {}'.format(bot1), 'python3 {}'.format(bot2)]
            results = json.loads(subprocess.check_output(args).decode('utf-8'))
            return results['stats']['0']['rank'] == 1

from scipy.optimize import minimize

result_queue = multiprocessing.JoinableQueue(1000)
task_queue = multiprocessing.JoinableQueue(1000)
NUM_WORKERS=8

for i in range(NUM_WORKERS):
    worker = Worker(task_queue, result_queue)
    worker.start()

import random
import sys

bot1 = sys.argv[1]
bot2 = sys.argv[2]
random.seed(4331999)

n = 9
runs = 200

seeds = [int(''.join(["%s" % random.randint(0, 9) for num in range(0, n)])) for i in range(runs)]
print("example seed", seeds[:2])

results= []
for i, seed in zip(range(runs), seeds):
    task_queue.put((bot1, bot2, seed))

while not len(results)==runs:
    results.append(result_queue.get())
    print(bot1, sum(results), len(results), 'w/r', sum(results)/len(results))

for i in range(NUM_WORKERS):
    task_queue.put(None)

print(bot1, sum(results)/len(results))
print(bot2, 1-sum(results)/len(results))

