#include "hlt/hlt.hpp"
#include "hlt/navigation.hpp"

float mexican_hat(float att, float G, float distance) {
    return att*2/(std::sqrt(3*G)*std::pow(3.141, 0.25))*(1-std::pow(distance/G, 2))*std::exp(-std::pow(distance, 2)/(2*std:pow(G, 2)));
}

int main( int argc, char *argv[] ) {
    const hlt::Metadata metadata = hlt::initialize("Vectorian.mod");
    const hlt::PlayerId player_id = metadata.player_id;
    const hlt::Map& initial_map = metadata.initial_map;
    
    //float weights[5] = {0.0099958, 0.00499792, 0.0099958, 0.0099958, 3.00042432};
    //float weights[5] = { 0.02, 0.02, 0.01, 0.01, 3.01 };
    // empty planet, my planet, enemy_planet enemy_ship, my_ship
    float weights[5] = { 0.0133615, 0.0133615, 0.00669743, 0.00669743, 2.00591877 };
    //{0.00110293, 1.10238807, 0.00166679, 0.00298913, 1.10238669};
    if (argc>1) {
        weights[0] = atof(argv[1]);
        weights[1] = atof(argv[2]);
        weights[2] = atof(argv[3]);
        weights[3] = atof(argv[4]);
        weights[4] = atof(argv[5]);
    } 

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
    hlt::Log::log("direction" + std::to_string(weights[0]));

    for (;;) {
        moves.clear();
        const hlt::Map map = hlt::in::get_map();

        for (const hlt::Ship& ship : map.ships.at(player_id)) {
            if (ship.docking_status != hlt::ShipDockingStatus::Undocked) {
                continue;
            }

            float x_contrib=0;
            float y_contrib=0;


            const hlt::Ship* closest_enemy_ship = map.get_closest_enemy_ship(ship);
            float distance = ship.location.get_distance_to(closest_enemy_ship->location);
            hlt::Log::log("Ship: "+std::to_string(ship.entity_id)+" at "+std::to_string(ship.location.pos_x)+" "+std::to_string(ship.location.pos_y)+" distance "+std::to_string(distance));
            if (distance > 40) {
                bool docked = false;
                for (const hlt::Planet& planet : map.planets) {
                    if (planet.is_full()){ continue; }

                    if (ship.can_dock(planet)) {
                        moves.push_back(hlt::Move::dock(ship.entity_id, planet.entity_id));
                        docked = true;
                        break;
                    }
                }
                if(docked==true) {continue;}
            }

            for (const hlt::Planet& planet : map.planets) {
                if (planet.is_full()){ continue; }
                float distance = ship.location.get_distance_to(planet.location);

                float G = weights[0];
                float sign = planet.free_spots();
                if (planet.owned and planet.owner_id == ship.owner_id){
                    G = weights[1];
                } else if (planet.owned and planet.owner_id != ship.owner_id) { 
                    G = weights[2];
                }

                float contrib = sign*std::exp(-G*distance*distance);
                //hlt::Log::log("Planet" + std::to_string(contrib));
                x_contrib += (planet.location.pos_x - ship.location.pos_x) * contrib;
                y_contrib += (planet.location.pos_y - ship.location.pos_y) * contrib;
            }

            for (std::pair<hlt::PlayerId, std::vector<hlt::Ship>> it : map.ships) {
                for (hlt::Ship ship2 : it.second) {
                    if (ship2.entity_id == ship.entity_id) { continue; }
                    
                    short sign = 1;
                    float G = weights[3];
                    if (ship2.owner_id == ship.owner_id) {
                        sign *= -1;
                        G = weights[4];
                    }

                    float distance = ship.location.get_distance_to(ship2.location);
                    float contrib = sign*std::exp(-G*distance*distance);
                    //hlt::Log::log("Ship" + std::to_string(contrib));

                    x_contrib += (ship2.location.pos_x - ship.location.pos_x) * contrib;
                    y_contrib += (ship2.location.pos_y - ship.location.pos_y) * contrib;
                }
            }

            hlt::Location new_direction = { x_contrib, y_contrib };
            new_direction = new_direction.normalize();
            hlt::Log::log("Ship: "+std::to_string(ship.entity_id)+" at "+std::to_string(ship.location.pos_x)+" "+std::to_string(ship.location.pos_y)+" to"+std::to_string(new_direction.pos_x)+" "+std::to_string(new_direction.pos_y));
            new_direction = new_direction.multiply(12);
            new_direction = ship.location.plus(new_direction);
            const hlt::possibly<hlt::Move> move = hlt::navigation::navigate_ship_towards_target(map, ship, new_direction, hlt::constants::MAX_SPEED, true, 50, 0.0872665);

            if (move.second) {
                moves.push_back(move.first);
            }
        }

        if (!hlt::out::send_moves(moves)) {
            hlt::Log::log("send_moves failed; exiting");
            break;
        }
    }
}
