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
botname = "TheDorian.vector.post"
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

def navigate(ship, target, game_map, speed, avoid_obstacles=True, max_corrections=20, angular_step=5):
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
            return navigate(ship, new_target, game_map, speed, True, max_corrections - 1, angular_step)

        return ship.thrust(speed, angle)

def sign(x):
    if x<0:
        return -1
    return 1

def get_closest_enemy_ship(entities_by_distance, my_ships):
    try:
        for distance in entities_by_distance:
            entity = entities_by_distance[distance][0]
            if not isinstance(entity, hlt.entity.Ship):
                continue

            if entity not in my_ships:
                return distance, entity
        return None, None
    except Exception as e:
        logging.error("{}".format(e))


def get_closest_dockable_planet(entities_by_distance, my_id):
    try:
        best_distance_per_slots, best_planet = 10000, None

        for distance in entities_by_distance:
            entity = entities_by_distance[distance][0]
            if not isinstance(entity, hlt.entity.Planet):
                continue

            if not entity.is_owned() or (not entity.is_full() and entity.all_docked_ships()[0].owner.id == my_id):
                if distance/entity.num_docking_spots < best_distance_per_slots:
                    best_distance_per_slots = distance/entity.num_docking_spots
                    best_planet = entity

        if best_planet is None:
            return None, None
        return best_distance_per_slots, best_planet
    except Exception as e:
        logging.error("{}".format(e))

ticks = 0
while True:
    try:
        ticks+=1
        game_map = game.update_map()
        # Here we define the set of commands to be sent to the Halite engine at the end of the turn

        my_id = game_map.get_me().id
        my_ships = game_map.get_me().all_ships()
        total_ships = sum(len(x.all_ships()) for x in game_map.all_players())

        logging.info("Tick {}".format(ticks))
        logging.info("NumPlayers: {}, AllShips: {}, EmptyPlanets: {}".format(len(game_map.all_players()), total_ships, sum(1 for x in game_map.all_planets() if not x.is_owned())))

        max_other_players_mining = 0
        player_with_best_economy = None
        living_players = 0

        for player in game_map.all_players():
                player_ships = len(player.all_ships())
                num_mining = sum(1 for x in player.all_ships() if x.docking_status == x.DockingStatus.DOCKED)

                logging.info("Player: {}, NumShips: {}, NumMiners: {}, NumPlanets: {} ".format(
                        player.id,
                        player_ships,
                        num_mining,
                        sum(1 for x in game_map.all_planets() if x.owner == player)
                    ))
        command_queue = []
        for ship in my_ships:
            if not ship.docking_status == ship.DockingStatus.UNDOCKED:
                #logging.info("docked, skipping {}".format(ship))
                continue

            entities_by_distance = OrderedDict(sorted(game_map.nearby_entities_by_distance(ship).items(), key=lambda x: x[0]))
            closest_planet_distance, closest_planet = get_closest_dockable_planet(entities_by_distance, my_id)

            if closest_planet and ship.can_dock(closest_planet) and (not closest_planet.is_owned() or (closest_planet.owner == game_map.get_me() and not closest_planet.is_full())):
                command = ship.dock(closest_planet)
                if command:
                    #logging.info("docking {} to {}".format(ship, planet))
                    command_queue.append(command)
                    continue

            closest_ship_distance, closest_ship = get_closest_enemy_ship(entities_by_distance, my_ships)

            #logging.info("moving {}".format(ship))
            global_x, global_y = 0, 0

            biases = {
                    "my_planet": {
                        0: (-1, 1),
                        1:( 1, 0.005),
                        2:( 1, 0.004),
                        3:( 1, 0.003),
                        4:( 1, 0.002),
                        5:( 1, 0.001),
                    },
                    "empty_planet": {
                        1:( 1, 0.05),
                        2:( 1, 0.004),
                        3:( 1, 0.003),
                        4:( 1, 0.002),
                        5:( 1, 0.001),
                    },
                    "enemy_planet": {
                        0:( 1, 0.001),
                        1:( 1, 0.001),
                        2:( 1, 0.002),
                        3:( 1, 0.003),
                        4:( 1, 0.004),
                        5: (1, 0.005),
                    },
                    "my_ship": (-1, 1),
                    "enemy_ship": (1, 0.06)
            }
            contribs = []

            for planet in game_map.all_planets():
                    num_open_spots = min(5, planet.num_docking_spots - len(planet.all_docked_ships()))
                    if not planet.is_owned():
                        att, G = biases['empty_planet'][num_open_spots]
                    elif planet.owner == game_map.get_me():
                        att, G = biases['my_planet'][num_open_spots]
                    else:
                        att, G = biases['enemy_planet'][num_open_spots]

                    distance = ship.calculate_distance_between(planet)
                    contrib = att*math.exp(-G*distance**2)
                    contrib_x = contrib*(planet.x-ship.x)
                    contrib_y = contrib*(planet.y-ship.y)

                    #logging.info("contrib {}, contrib(x={}, y={}), distance {}, att {}, G {}, my(x={}, y={}), curmov(x={}, y={}), object: {}".format(contrib, contrib_x, contrib_y, distance, att, G, ship.x, ship.y, global_x, global_y, planet))
                    global_x += contrib_x
                    global_y += contrib_y


            for player in game_map.all_players():
                for s2 in player.all_ships():
                    if s2.id == ship.id:
                        continue

                    if s2.owner == game_map.get_me():
                        att, G = biases['my_ship']
                    else:
                        att, G = biases['enemy_ship']

                    distance = ship.calculate_distance_between(s2)
                    contrib = att*math.exp(-G*distance**2)

                    contrib_x = contrib*(s2.x-ship.x)
                    contrib_y = contrib*(s2.y-ship.y)


                    #logging.info("contrib {}, contrib(x={}, y={}), distance {}, my(x={}, y={}), curmov(x={}, y={}), object: {}".format(contrib, contrib_x, contrib_y, distance, ship.x, ship.y, global_x, global_y, s2))

                    global_x += contrib_x
                    global_y += contrib_y

            new_position = hlt.entity.Position(ship.x+global_x, ship.y+global_y)
            distance_to_pos = ship.calculate_distance_between(new_position)

            new_x = ship.x+global_x
            new_y = ship.y+global_y

            target_position = hlt.entity.Position(new_x, new_y)

            logging.info("moving from {} {} in {} {}, dist {} to {} {}".format(ship.x, ship.y, global_x, global_y, distance_to_pos, new_x, new_y))


            speed = 7
#           want_angle = ship.calculate_angle_between(target_position)
#           if closest_ship:
#               angle = ship.calculate_angle_between(closest_ship)
#               if abs(angle-want_angle)<10:
#                   speed = min(speed, closest_ship_distance)

#           if closest_planet:
#               angle = ship.calculate_angle_between(closest_planet)
#               if abs(angle-want_angle)<10:
#                   speed = min(speed, closest_planet_distance)

            navigate_command = navigate(ship,
                    target_position,
                    game_map,
                    speed=speed)

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
