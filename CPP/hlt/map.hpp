#pragma once

#include "map.hpp"
#include "types.hpp"
#include "ship.hpp"
#include "planet.hpp"

namespace hlt {
    class Map {
    public:
        int map_width, map_height;

        std::unordered_map<PlayerId, std::vector<Ship>> ships;
        std::unordered_map<PlayerId, entity_map<unsigned int>> ship_map;

        std::vector<Planet> planets;
        entity_map<unsigned int> planet_map;

        Map(int width, int height);

        const std::vector<Ship> all_ships() const {
            std::vector<Ship> all_ships_vect;

            for (std::pair<hlt::PlayerId, std::vector<hlt::Ship>> it : ships) {
                for (hlt::Ship ship : it.second) {
                    all_ships_vect.push_back(ship);
                }
            }

            return all_ships_vect;
        }

        const Planet* get_closest_dockable_planet(const Ship& ship) const {
            float closest_distance = 1000000;
            const Planet* closest_planet = NULL;
            for (const Planet& planet : planets) {
                if ((planet.owned && planet.owner_id != ship.owner_id) || planet.is_full()) { continue; }

                float distance = ship.location.get_distance_to(planet.location);
                if (distance<closest_distance) {
                    closest_distance = distance;
                    closest_planet = &planet;
                }
            }
            return closest_planet;
        }

        const Ship* get_closest_enemy_ship(const Ship& ship) const {
            float closest_distance = 100000;
            Ship* closest_ship = NULL;
            for (std::pair<PlayerId, std::vector<Ship>> it : ships) {
                if (it.first == ship.owner_id) { continue; }

                for (Ship enemy_ship : it.second) {
                    float distance = ship.location.get_distance_to(enemy_ship.location);
                    if (distance<closest_distance) {
                        closest_distance = distance;
                        closest_ship = &enemy_ship;
                    }
                }
            }
            return closest_ship;
        }

//      const std::vector<Entity> get_all_entities() const {
//          std::vector<Entity> entities;

//          for (std::pair<hlt::PlayerId, std::vector<hlt::Ship>> it : ships) {
//              for (hlt::Ship ship : it.second) {
//                  entities.insert(ship);
//              }
//          }

//          for (const hlt::Planet& planet : planets) {
//                  entities.insert(planet);
//          }

//          return entities;
//      }

        const Ship& get_ship(const PlayerId player_id, const EntityId ship_id) const {
            return ships.at(player_id).at(ship_map.at(player_id).at(ship_id));
        }

        const Planet& get_planet(const EntityId planet_id) const {
            return planets.at(planet_map.at(planet_id));
        }
    };
}
