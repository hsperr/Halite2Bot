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
# Then let's import the logging module so we can print out information
import logging
import math
from collections import OrderedDict, defaultdict

# GAME START
# Here we define the bot's name as Settler and initialize the game, including communication with the Halite engine.

botname = "Borian"
game = hlt.Game(botname)

ticks = 0
while True:
    try:
        ticks+=1
        game_map = game.update_map()
        # Here we define the set of commands to be sent to the Halite engine at the end of the turn
        command_queue = []

        # Send our set of commands to the Halite engine for this turn
        game.send_command_queue(command_queue)
        # TURN END
    except Exception as e:
        logging.error("Main: {}".format(e))
        break
    # GAME END
