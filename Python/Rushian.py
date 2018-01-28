"""
Welcome to your first Halite-II bot!

This bot's name is Settler. It's purpose is simple (don't expect it to win complex games :) ):
1. Initialize game
2. If a ship is not docked and there are unowned planets
2.a. Try to Dock in the planet if close enough
2.b If not, go towards the planet

Note: Please do not place print statements here as they are used to communicate with the Halite engine. If you need
to log anything use the logging module.
"""
# Let's start by importing the Halite Starter Kit so we can interface with the Halite engine
import hlt
import random
# Then let's import the logging module so we can print out information
import logging
import math
from collections import OrderedDict, defaultdict

# GAME START
# Here we define the bot's name as Settler and initialize the game, including communication with the Halite engine.
botname = "Rushian"
game = hlt.Game(botname)

def get_closest_enemy_ship(entities_by_distance, my_ships, player=None, force_docked=False):
    try:
        closest_solution = None, None

        for distance in entities_by_distance:
            entity = entities_by_distance[distance][0]
            if not isinstance(entity, hlt.entity.Ship):
                continue

            if entity not in my_ships and (not player or entity.owner.id==player):
                if force_docked:
                    if entity.docking_status != entity.DockingStatus.DOCKED:
                        closest_solution = distance, entity
                    else:
                        return distance, entity
                else:
                    return distance, entity
        return closest_solution
    except Exception as e:
        logging.error("{}".format(e))

def attack(ship, game_map, player=None, force_docked=False):
    job2ids[ATTACKER].add(ship.id)
    entities_by_distance = OrderedDict(sorted(game_map.nearby_entities_by_distance(ship).items(), key=lambda x: x[0]))

    closest_ship_distance, clostest_enemy_ship = get_closest_enemy_ship(entities_by_distance, game_map.get_me().all_ships())
    target_distance, target_ship = closest_ship_distance, clostest_enemy_ship
    navigate_command = ship.navigate(ship.closest_point_to(target_ship),
            game_map,
            speed=int(hlt.constants.MAX_SPEED))
            

    return navigate_command

ticks = 0

job2ids = defaultdict(set)

ATTACKER = 'attacker'
MINER = 'miner'

targets = set()

while True:
    try:
        ticks+=1
        game_map = game.update_map()
        # Here we define the set of commands to be sent to the Halite engine at the end of the turn
        command_queue = []

        for ship in game_map.get_me().all_ships():
           command = attack(ship, game_map)
           if command:
               command_queue.append(command)
                # Send our set of commands to the Halite engine for this turn
        game.send_command_queue(command_queue)
        # TURN END
    except Exception as e:
        logging.error("Main: {}".format(e))
        break
    # GAME END
