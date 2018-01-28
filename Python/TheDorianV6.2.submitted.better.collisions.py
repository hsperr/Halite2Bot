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
botname = "TheDorian.V6.2"
game = hlt.Game(botname)

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

def obstacles_between(ship, target, entities_by_distance, ignore=()):
    """
    Check whether there is a straight-line path to the given point, without planetary obstacles in between.
    :param entity.Ship ship: Source entity
    :param entity.Entity target: Target entity
    :return: The list of obstacles between the ship and target
    :rtype: list[entity.Entity]
    """

    entities = []
    for dist, ents in entities_by_distance.items():
        if dist<10:
            entities.extend(ents)

    obstacles = []
    for foreign_entity in entities:
        if foreign_entity == ship or foreign_entity == target:
            continue
        if hlt.collision.intersect_segment_circle(ship, target, foreign_entity, fudge=ship.radius + 0.1):
            obstacles.append(foreign_entity)
    return obstacles

def navigate(ship, target, game_map, speed, entities_by_distance, avoid_obstacles=True, max_corrections=50, angular_step=5):
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
        if avoid_obstacles and obstacles_between(ship, target, entities_by_distance):
            new_target_dx = math.cos(math.radians(angle + angular_step)) * distance
            new_target_dy = math.sin(math.radians(angle + angular_step)) * distance
            new_target = hlt.entity.Position(ship.x + new_target_dx, ship.y + new_target_dy)
            return navigate(ship, new_target, game_map, speed, entities_by_distance, True, max_corrections - 1, angular_step)
        speed = speed if (distance >= speed) else distance
        return ship.thrust(speed, angle)

def mine(ship, game_map):
    entities_by_distance = OrderedDict(sorted(game_map.nearby_entities_by_distance(ship).items(), key=lambda x: x[0]))
    distance, closest_dockable_planet = get_closest_dockable_planet(entities_by_distance, game_map.get_me().id)

    if not distance:
        #logging.info("Wanted to mine, attacking instead {}".format(ship.id, distance, closest_dockable_planet))
        if ship.id in job2ids[MINER]:
            job2ids[MINER].remove(ship.id)
            
        return attack(ship, game_map)

    #logging.info("Miner {}, distance: {} target: {}".format(ship.id, distance, closest_dockable_planet))

    job2ids[MINER].add(ship.id)

    if ship.can_dock(closest_dockable_planet):
        #logging.info("docking ship:{}, to: {}".format(ship, closest_dockable_planet))
        return ship.dock(closest_dockable_planet)
    else:
        #logging.info("navigating ship:{}, to: {}".format(ship, closest_dockable_planet))
        speed = min(int(hlt.constants.MAX_SPEED), max(ship.id*4, ticks))
        navigate_command = navigate(ship,
                ship.closest_point_to(closest_dockable_planet),
                game_map,
                speed,
                entities_by_distance,
                avoid_obstacles=True,
                max_corrections=120)
        return navigate_command

def attack(ship, game_map, player=None, force_docked=False):
    job2ids[ATTACKER].add(ship.id)
    entities_by_distance = OrderedDict(sorted(game_map.nearby_entities_by_distance(ship).items(), key=lambda x: x[0]))

    closest_ship_distance, clostest_enemy_ship = get_closest_enemy_ship(entities_by_distance, game_map.get_me().all_ships())
    target_distance, target_ship = closest_ship_distance, clostest_enemy_ship

    if force_docked:
        closest_docked_ship_distance, closest_docked_ship = get_closest_enemy_ship(entities_by_distance, game_map.get_me().all_ships(), player=player, force_docked=force_docked)
        if closest_docked_ship_distance < closest_ship_distance*1.2:
            target_distance, target_ship = closest_docked_ship_distance, closest_docked_ship

    for target in targets: 
        distance = ship.calculate_distance_between(target)
        if distance < target_distance * 1.3:
            target_distance, target_ship = distance, target

    targets.add(target_ship)

    #logging.info("Attacker {}, distance: {} target: {}".format(ship.id, player_ship_distance, closest_enemy_ship))
    navigate_command = ship.navigate(
            ship.closest_point_to(target_ship),
            game_map,
            int(hlt.constants.MAX_SPEED),
            entities_by_distance,
            ignore_ships=False)

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

        my_ships = game_map.get_me().all_ships()
        free_ships = [x for x in my_ships if x.docking_status == x.DockingStatus.UNDOCKED and x.id not in job2ids[ATTACKER] and x.id not in job2ids[MINER] ]
        total_ships = sum(len(x.all_ships()) for x in game_map.all_players())


        targets = set([game_map.get_player(x.owner.id).get_ship(x.id) for x in targets if game_map.get_player(x.owner.id).get_ship(x.id) and game_map.get_player(x.owner.id).get_ship(x.id).health > 0])

        my_id = game_map.get_me().id
        living_shipids = set(x.id for x in my_ships)
        job2ids[MINER] = job2ids[MINER].intersection(living_shipids)
        job2ids[ATTACKER] = job2ids[ATTACKER].intersection(living_shipids)

        logging.info("Tick {}".format(ticks))
        logging.info("Me: {}, Ships: {}, FreeShips: {}".format(my_id, len(my_ships), len(free_ships)))
        logging.info("NumPlayers: {}, AllShips: {}, EmptyPlanets: {}".format(len(game_map.all_players()), total_ships, sum(1 for x in game_map.all_planets() if not x.is_owned())))

        max_other_players_mining = 0
        player_with_best_economy = None
        living_players = 0

        for player in game_map.all_players():
                player_ships = len(player.all_ships())
                if player_ships >0:
                    living_players+=1
                num_mining = sum(1 for x in player.all_ships() if x.docking_status == x.DockingStatus.DOCKED)

                if num_mining>max_other_players_mining and not player.id == my_id:
                    max_other_players_mining = num_mining
                    player_with_best_economy = player.id

                logging.info("Player: {}, NumShips: {}, NumMiners: {}, NumPlanets: {} ".format(
                        player.id,
                        player_ships,
                        num_mining,
                        sum(1 for x in game_map.all_planets() if x.owner == player)
                    ))

        if ticks == 1:
            if len(game_map.all_players())==2:
                num_ships_rushing = int(random.random()*2)
                for ship in free_ships:
                   logging.info("Rushing with {}, {}<{}".format(num_ships_rushing, game_map.width * game_map.height, 260*170))
                   if len(job2ids[ATTACKER])<num_ships_rushing and game_map.width * game_map.height < 260*170:
                       command = attack(ship, game_map)
                       if command:
                           command_queue.append(command)
                   else:
                        command = mine(ship, game_map)
                        if command:
                            command_queue.append(command)
            else:
                for ship in free_ships:
                    command = mine(ship, game_map)
                    if command:
                        command_queue.append(command)
        else:
            for ship in my_ships:
                if ship.docking_status != ship.DockingStatus.UNDOCKED:
#                   if not one_undocked:
#                       entities_by_distance = OrderedDict(sorted(game_map.nearby_entities_by_distance(ship).items(), key=lambda x: x[0]))
#                       enemy_ship_count, my_ship_count = 0, 0
#                       for distance, entities in entities_by_distance.items():
#                           if distance > 10:
#                               break

#                           enemy_ship_count += sum(1 for x in entities if isinstance(x, hlt.entity.Ship) and not x.owner==game_map.get_me())
#                           my_ship_count += sum(1 for x in entities if isinstance(x, hlt.entity.Ship) and x.owner==game_map.get_me())


#                       if enemy_ship_count>my_ship_count and ship.docking_status == ship.DockingStatus.DOCKED:
#                           one_undocked = True
#                           logging.info("Undocking to attack: {} {}".format(ship, entities))
#                           command_queue.append(ship.undock())
#                           job2ids[ATTACKER].add(ship.id)
#                           break
                    continue
                best_economy = len(job2ids[MINER]) >= max(len(game_map.all_players()), max_other_players_mining+2)

                if ship.id in job2ids[ATTACKER]:
                    command = attack(ship, game_map, player=player_with_best_economy, force_docked=best_economy)
                    if command:
                        command_queue.append(command)
                elif ship.id in job2ids[MINER]:
                    command = mine(ship, game_map)
                    if command:
                        command_queue.append(command)
                else:
                    if best_economy:
                        if ship.id%6==0:
                            command = mine(ship, game_map)
                            if command:
                                command_queue.append(command)
                        else:
                            if living_players==2:
                                if best_economy:
                                    command = attack(ship, game_map)
                                else:
                                    command = attack(ship, game_map, force_docked=True)
                            else:
                                command = attack(ship, game_map, player=player_with_best_economy, force_docked=best_economy)

                            if command:
                                command_queue.append(command)
                    elif ship.id % 6 == 0:
                        command = attack(ship, game_map, player=player_with_best_economy, force_docked=best_economy)
                        if command:
                            command_queue.append(command)
                    else:
                        command = mine(ship, game_map)
                        if command:
                            command_queue.append(command)


        # Send our set of commands to the Halite engine for this turn
        game.send_command_queue(command_queue)
        # TURN END
    except Exception as e:
        logging.error("Main: {}".format(e))
        break
    # GAME END
