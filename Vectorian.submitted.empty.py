import hlt
import logging
import math
from collections import OrderedDict, defaultdict
import sys

biases = {
        "my_planet": (1, 0.02),
        "empty_planet": (1, 0.02),
        "enemy_planet": (1, 0.01),
        "my_ship": (-1, 0.01),
        "enemy_ship": (1, 0.01)
}
botname = "Vectorian"

if len(sys.argv) ==2:
    weights = [float(x) for x in sys.argv[1].split("#")]
    biases = {
            "my_planet": (1, weights[0]),
            "empty_planet": (1, weights[1]),
            "enemy_planet": (1, weights[2]),
            "my_ship": (-1, weights[3]),
            "enemy_ship": (1, weights[4])
    }

    botname = "Vect"+sys.argv[1]

game = hlt.Game(botname)

def obstacles_between(ship, target, ignore=(), fudge=0.1):
    """
    Check whether there is a straight-line path to the given point, without planetary obstacles in between.

    :param entity.Ship ship: Source entity
    :param entity.Entity target: Target entity
    :param entity.Entity ignore: Which entity type to ignore
    :return: The list of obstacles between the ship and target
    :rtype: list[entity.Entity]
    """
    obstacles = []
    entities = ([] if issubclass(hlt.entity.Planet, ignore) else game_map.all_planets()) \
        + ([] if issubclass(hlt.entity.Ship, ignore) else game_map._all_ships())
    for foreign_entity in entities + move_targets:
        if foreign_entity == ship or foreign_entity == target:
            continue
        if hlt.collision.intersect_segment_circle(ship, target, foreign_entity, fudge=ship.radius + fudge):
            obstacles.append(foreign_entity)
    return obstacles

def navigate(ship, target, game_map, speed, avoid_obstacles=True, max_corrections=90, angular_step=5):
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
        if avoid_obstacles:
            obstacles = obstacles_between(ship, target)
            if obstacles:
                new_target = ship + hlt.entity.Position(math.cos(math.radians(angle + angular_step)) * distance, math.sin(math.radians(angle + angular_step)) * distance)
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


move_targets = []

ticks = 0

def radial(att, G, distance):
    return att*math.exp(-G*distance**2)

def mexican_hat(att, G, distance):
    return att*2/(math.sqrt(3*G)*3.141**(0.25))*(1-(distance/G)**2)*math.exp(-distance**2/(2*G**2))

while True:
    try:
        ticks+=1
        game_map = game.update_map()

        my_id = game_map.get_me().id
        my_ships = game_map.get_me().all_ships()
        #total_ships = sum(len(x.all_ships()) for x in game_map.all_players())
        #logging.info("Tick {}".format(ticks))
        #logging.info("NumPlayers: {}, AllShips: {}, EmptyPlanets: {}".format(len(game_map.all_players()), total_ships, sum(1 for x in game_map.all_planets() if not x.is_owned())))
        #for player in game_map.all_players():
        #        player_ships = len(player.all_ships())
        #        num_mining = sum(1 for x in player.all_ships() if x.docking_status == x.DockingStatus.DOCKED)

        #        logging.info("Player: {}, NumShips: {}, NumMiners: {}, NumPlanets: {} ".format(
        #               player.id,
        #               player_ships,
        #               num_mining,
        #               sum(1 for x in game_map.all_planets() if x.owner == player)
        #           ))
        command_queue = []
        move_targets = []
        done = 0
        for ship in my_ships:
            if not ship.docking_status == ship.DockingStatus.UNDOCKED:
                continue

            entities_by_distance = OrderedDict(sorted(game_map.nearby_entities_by_distance(ship).items(), key=lambda x: x[0]))
            closest_planet_distance, closest_planet = get_closest_dockable_planet(entities_by_distance, my_id)
            closest_ship_distance, closest_ship = get_closest_enemy_ship(entities_by_distance, my_ships)

            if closest_planet:
                can_dock = ship.can_dock(closest_planet)
                empty_or_free = (not closest_planet.is_owned() or (closest_planet.owner == game_map.get_me() and not closest_planet.is_full()))
                enemy_close = closest_ship_distance and ship.calculate_distance_between(closest_ship) < 12

                if closest_planet and can_dock and empty_or_free and not enemy_close:
                    command = ship.dock(closest_planet)
                    if command:
                        command_queue.append(command)
                        continue

            global_x, global_y = 0, 0
            contribs = []

            for entity in game_map.all_planets()+game_map.all_ships():
                if entity == ship:
                    continue

                contrib_func = radial
                distance = ship.calculate_distance_between(entity)

                if isinstance(entity, hlt.entity.Planet):
                    if not entity.is_owned():
                        att, G = biases['empty_planet']
                        att = entity.num_spots_left() + ticks/100
                    elif entity.owner == game_map.get_me():
                        att, G = biases['my_planet']
                        if entity.is_full():
                            att = 0
                    else:
                        att, G = biases['enemy_planet']
                if isinstance(entity, hlt.entity.Ship):
                    if entity.owner == game_map.get_me():
                        att, G = biases['my_ship']
                        contrib_func = mexican_hat
                    else:
                        att, G = biases['enemy_ship']

                contrib = contrib_func(att, G, distance)

                contrib_x = contrib*(entity.x-ship.x)
                contrib_y = contrib*(entity.y-ship.y)

                global_x += contrib_x
                global_y += contrib_y

#               logging.info("CONTRIB *************")
#               logging.info("CONTRIB tick {}, ship {}".format(ticks,ship))
#               logging.info("CONTRIB tick {}, target {}".format(ticks, entity))
#               logging.info("CONTRIB tick {}, distance {}".format(ticks,distance))
#               logging.info("CONTRIB tick {}, att, G {} {}".format(ticks,att, G))
#               logging.info("CONTRIB tick {}, contrib {}".format(ticks,contrib))
#               logging.info("CONTRIB tick {}, contrib x/y {} {}".format(ticks, contrib_x, contrib_y))
#               logging.info("CONTRIB tick {}, global x/y {} {}".format(ticks, global_x,global_y))
                

            target = hlt.entity.Position(global_x, global_y)
            target = target.normalize()
            target = target * 12
            target = ship.get_position()+target

            distance = ship.calculate_distance_between(target)
            speed = 7

#            logging.info("tick {}, Ship {} {}, target {}, distance {}".format(ticks, ship.x, ship.y, target, distance))

#           obstacles = list(filter(lambda x: not x == ship, obstacles_between(ship, target)))
#           for obstacle in obstacles:
#               distance_to_obstacle = target.calculate_distance_between(obstacle)
#               logging.info("Distance to obstacle {} {} {}".format(distance_to_obstacle, not obstacle == ship, ship))
#               if not obstacle == ship and distance_to_obstacle:
#                   distance_to_obstacle = ship.calculate_distance_between(ship.closest_point_to(obstacle))
#                   speed = min(speed, distance_to_obstacle)

#                   clos_x, clos_y = hlt.collision.closest_point_on_path_to(ship, target, obstacle, fudge=ship.radius+0.1)
#                   closest_point = hlt.entity.Position(clos_x, clos_y)
#                   avoid = (closest_point - obstacle).normalize() * 7
#                   logging.info("Ship {}".format(ship))
#                   logging.info("Target {}".format(target))
#                   logging.info("Obstacle {}".format(obstacle))
#                   logging.info("closest point {}".format(closest_point))
#                   logging.info("distance {}".format(distance_to_obstacle))
#                   logging.info("avoid {}".format(avoid))
#                   target = target + avoid
#                   logging.info("new target {}".format(target))

#               
#           angle = ship.calculate_angle_between(target)
#           logging.info("Obstacles {} angle {} speed {}".format(obstacles, angle, speed))
#           command_queue.append(ship.thrust(speed, angle))

            command = navigate(ship, target, game_map, 7)
            if command:
                move_targets.append(target)
                command_queue.append(command)
        # Send our set of commands to the Halite engine for this turn
        game.send_command_queue(command_queue)
        target = None
        # TURN END
    except Exception as e:
        logging.error("Main: {}".format(e))
        break
    # GAME END
