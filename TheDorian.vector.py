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
botname = "TheDorian.V6.1"
game = hlt.Game(botname)

def obstacles_between(ship, target):
    """
    Check whether there is a straight-line path to the given point, without planetary obstacles in between.
    :param entity.Ship ship: Source entity
    :param entity.Entity target: Target entity
    :return: The list of obstacles between the ship and target
    :rtype: list[entity.Entity]
    """
    obstacles = []
    for foreign_entity in game_map.all_planets() + game_map.all_ships():
        if foreign_entity == target:
            continue
        if collision.intersect_segment_circle(ship, target, foreign_entity, fudge=ship.radius + 0.1):
            obstacles.append(foreign_entity)
    return obstacles

def navigate(ship, target, game_map, speed, avoid_obstacles=True, max_corrections=50, angular_step=5):
        """
        Move a ship to a specific target position (Entity). It is recommended to place the position
        itself here, else navigate will crash into the target. If avoid_obstacles is set to True (default)
        will avoid obstacles on the way, with up to max_corrections corrections. Note that each correction accounts
        for angular_step degrees difference, meaning that the algorithm will naively try max_correction degrees before giving
        up (and returning None). The navigation will only consist of up to one command; call this method again
        in the next turn to continue navigating to the position.
        :param Entity target: The entity to which you will navigate
        :param game_map.Map game_map: The map of the game, from which obstacles will be extracted
        :param int speed: The (max) speed to navigate. If the obstacle is nearer, will adjust accordingly.
        :param bool avoid_obstacles: Whether to avoid the obstacles in the way (simple pathfinding).
        :param int max_corrections: The maximum number of degrees to deviate per turn while trying to pathfind.
        If exceeded returns None.
        :param int angular_step: The degree difference to deviate if the original destination has obstacles
        :return string: The command trying to be passed to the Halite engine or None if movement is not possible
        within max_corrections degrees.
        :rtype: str
        """
        # Assumes a position, not planet (as it would go to the center of the planet otherwise)
        if max_corrections <= 0:
            return None
        distance = ship.calculate_distance_between(target)
        angle = ship.calculate_angle_between(target)
        if avoid_obstacles and game_map.obstacles_between(ship, target):
            new_target_dx = math.cos(math.radians(angle + angular_step)) * distance
            new_target_dy = math.sin(math.radians(angle + angular_step)) * distance
            new_target = hlt.entity.Position(ship.x + new_target_dx, ship.y + new_target_dy)
            return ship.navigate(new_target, game_map, speed, True, max_corrections - 1, angular_step)
        speed = speed if (distance >= speed) else distance
        return ship.thrust(speed, angle)

ticks = 0
def sign(x):
    if x<0:
        return -1
    return 1


while True:
    try:
        ticks+=1
        game_map = game.update_map()
        # Here we define the set of commands to be sent to the Halite engine at the end of the turn
        command_queue = []
        for ship in game_map.get_me().all_ships():
            if not ship.docking_status == ship.DockingStatus.UNDOCKED:
                logging.info("docked, skipping {}".format(ship))
                continue

            done = False
            for planet in game_map.all_planets():
                if ship.can_dock(planet) and (not planet.is_owned() or (planet.owner == game_map.get_me() and not planet.is_full())):
                    command = ship.dock(planet)
                    if command:
                        logging.info("docking {} to {}".format(ship, planet))
                        command_queue.append(command)
                        done = True
                        break
            if done:
                continue

            logging.info("moving {}".format(ship))
            global_x, global_y = 0, 0

            biases = {
                    "my_planet": {
                        0: 1000.0,
                        1: 0.1,
                        2: 0.01,
                        3: 0.001,
                        4: 0.001,
                        5: 0.0001,
                    },
                    "empty_planet": {
                        1: 0.01,
                        2: 0.001,
                        3: 0.001,
                        4: 0.00001,
                        5: 0.0000001,
                    },
                    "enemy_planet": {
                        0: 0.0001,
                        1: 0.001,
                        2: 0.01,
                        3: 0.1,
                        4: 0.1,
                        5: 0.1,
                    },
                    "my_ship": 0.0005,
                    "enemy_ship": 0.00001
            }
            attractions = {
                    "my_planet": 1,
                    "empty_planet": 1,
                    "enemy_planet": 1,
                    "my_ship": -1,
                    "enemy_ship": 10
            }
            contribs = []
            for planet in game_map.all_planets():
                    num_open_spots = min(5, planet.num_docking_spots - len(planet.all_docked_ships()))
                    if not planet.is_owned():
                        att = attractions['empty_planet']
                        G = biases['empty_planet'][num_open_spots]
                    elif planet.owner == game_map.get_me():
                        att = attractions['my_planet']
                        G = biases['my_planet'][num_open_spots]
                    else:
                        att = attractions['enemy_planet']
                        G = biases['enemy_planet'][num_open_spots]

                    distance = ship.calculate_distance_between(planet)
                    contrib = att*math.exp(-G*distance**2)
                    contrib_x = contrib*(planet.x-ship.x)/distance
                    contrib_y = contrib*(planet.y-ship.y)/distance

                    global_x += contrib_x
                    global_y += contrib_y

                    contribs.append({
                        "from": ship,
                        "entity": planet,
                        "distance": ship.calculate_distance_between(planet),
                       "contrib": contrib,
                       "contrib_x": contrib_x,
                       "contrib_y": contrib_y,
                        })

#                   logging.info("planet  {}".format(planet))
#                   logging.info("att {} G {} dist {}".format(att, G, ship.calculate_distance_between(planet)))
#                   logging.info("contrib {}".format(contrib))
#                   logging.info("contrib_x {}".format(contrib_x))
#                   logging.info("contrib_y {}".format(contrib_y))
#                   logging.info("global_x {}".format(global_x))
#                   logging.info("global_y {}".format(global_y))

            for player in game_map.all_players():
                for s2 in player.all_ships():
                    if s2.id == ship.id:
                        continue

                    if s2.owner == game_map.get_me():
                        att = attractions['my_ship']
                        G = biases['my_ship']
                    else:
                        att = attractions['enemy_ship']
                        G = biases['enemy_ship']

                    distance = ship.calculate_distance_between(s2)
                    contrib = att*math.exp(-G*distance**2)
                    contrib_x = contrib*(s2.x-ship.x)/distance
                    contrib_y = contrib*(s2.y-ship.y)/distance

                    contribs.append({
                        "from": ship,
                        "entity": s2,
                        "distance": ship.calculate_distance_between(s2),
                       "contrib": contrib,
                       "contrib_x": contrib_x,
                       "contrib_y": contrib_y,
                        })

#                   logging.info("ship  {}, owner {}".format(s2, s2.owner.id))
#                   logging.info("att {} G {} dist {}".format(att, G, ship.calculate_distance_between(s2)))
#                   logging.info("ship.x {} ship.y {}".format(ship.x, ship.y))
#                   logging.info("contrib {}".format(contrib))
#                   logging.info("contrib_x {}".format(contrib_x))
#                   logging.info("contrib_y {}".format(contrib_y))
#                   logging.info("global_x {}".format(global_x))
#                   logging.info("global_y {}".format(global_y))

            for entry in sorted(contribs, key=lambda x: (str(x['from']), x['distance'])):
                #global_x, global_y = entry['contrib_x'], entry['contrib_y']
                logging.info("{}".format(entry))
                #break

            logging.info("moving from {} {} to {} {}".format(ship.x, ship.y, ship.x+global_x, ship.y+global_y))


            navigate_command = ship.navigate(
                    hlt.entity.Position(ship.x+global_x*7, ship.y+global_y*7),
                    game_map,
                    speed=int(hlt.constants.MAX_SPEED),
                    ignore_ships=True)

            if navigate_command:
                command_queue.append(navigate_command)
        # Send our set of commands to the Halite engine for this turn
        game.send_command_queue(command_queue)
        target = None
        # TURN END
    except Exception as e:
        logging.error("Main: {}".format(e))
        break
    # GAME END
