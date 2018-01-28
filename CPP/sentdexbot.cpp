#include "hlt/hlt.hpp"
#include "hlt/navigation.hpp"


int main( int argc, char *argv[] ) {
    const hlt::Metadata metadata = hlt::initialize("Sentdexbot");
    const hlt::PlayerId player_id = metadata.player_id;

    const hlt::Map& initial_map = metadata.initial_map;

    // We now have 1 full minute to analyse the initial map.
    std::ostringstream initial_map_intelligence;
    initial_map_intelligence
            << "width: " << initial_map.map_width
            << "; height: " << initial_map.map_height
            << "; players: " << initial_map.ship_map.size()
            << "; my ships: " << initial_map.ship_map.at(player_id).size()
            << "; planets: " << initial_map.planets.size();
    hlt::Log::log(initial_map_intelligence.str());

    std::vector<hlt::Move> moves;
    for (;;) {
        moves.clear();
        const hlt::Map map = hlt::in::get_map();

        for (const hlt::Ship& ship : map.ships.at(player_id)) {
            if (ship.docking_status != hlt::ShipDockingStatus::Undocked) {
                continue;
            }

            const hlt::Planet* closest_undocked_planet = map.get_closest_dockable_planet(ship);

            const hlt::Ship* closest_enemy_ship = map.get_closest_enemy_ship(ship);
            float enemy_ship_distance = ship.location.get_distance_to(closest_enemy_ship->location);

            if (closest_undocked_planet != NULL) {
                float distance = ship.location.get_distance_to(closest_undocked_planet->location);
                if (distance < enemy_ship_distance) {
                     if (ship.can_dock(*closest_undocked_planet)) {
                         moves.push_back(hlt::Move::dock(ship.entity_id, closest_undocked_planet->entity_id));
                         continue;
                     }

                    const hlt::possibly<hlt::Move> move = hlt::navigation::navigate_ship_to_dock(map, ship, *closest_undocked_planet, hlt::constants::MAX_SPEED);
                    if (move.second) {
                        moves.push_back(move.first);
                        continue;
                    }
                } else {
                    const hlt::possibly<hlt::Move> move = hlt::navigation::navigate_ship_to_dock(map, ship, *closest_enemy_ship, hlt::constants::MAX_SPEED);
                    hlt::Log::log("Ship" +std::to_string(ship.entity_id)+"enemy_ship_distance" + std::to_string(enemy_ship_distance)+"---"+std::to_string(closest_enemy_ship->entity_id));

                    if (move.second) {
                        moves.push_back(move.first);
                        continue;
                    }
                }
            } else {
                const hlt::possibly<hlt::Move> move = hlt::navigation::navigate_ship_to_dock(map, ship, *closest_enemy_ship, hlt::constants::MAX_SPEED);
                hlt::Log::log("Ship" +std::to_string(ship.entity_id)+"enemy_ship_distance" + std::to_string(enemy_ship_distance)+"---"+std::to_string(closest_enemy_ship->entity_id));

                if (move.second) {
                    moves.push_back(move.first);
                    continue;
                }
            }
        }

        if (!hlt::out::send_moves(moves)) {
            hlt::Log::log("send_moves failed; exiting");
            break;
        }
    }
}

