
#include "Arduino.h"
#include "DCDoor.h"
#include "Interface.h"


TwoWayMagnet::TwoWayMagnet(JsonObject conf) : Interface("TwoWayMagnet", strdup(conf["name"].as<const char*>()))
{
    if (!conf.containsKey("first_direction_pin")) {
    send_error("Missing 'first_direction_pin' key in config");
    return;
    }
    if (!conf.containsKey("second_direction_pin")) {
    send_error("Missing 'second_direction_pin' key in config");
    return;
    }
    if (!conf["first_direction_pin"].is<int>() || !conf["second_direction_pin"].is<int>()) {
      send_error("pins: Each element should be an integer");
      return;
    }

    first_direction_pin = conf["first_direction_pin"].as<int>();
    second_direction_pin = conf["second_direction_pin"].as<int>();
    pinMode(first_direction_pin, OUTPUT);
    pinMode(second_direction_pin, OUTPUT);
    off();
    prev_time = millis();
    time_gap = 1000;
}

void TwoWayMagnet::off(){
    digitalWrite(first_direction_pin, LOW);
    digitalWrite(second_direction_pin, LOW);
    state = 0;
}


void TwoWayMagnet::get_value(JsonDocument* container){
}

void TwoWayMagnet::run(JsonArray cmd){
    const char* action = cmd[0]; // "first" or "second"
    if (strcmp(action, "first") == 0) {
        direction = 0;
    } else if (strcmp(action, "second") == 0) {
        direction = 1;
    } else {
        // Handle error or other actions
    }
    state = 1;
}

void TwoWayMagnet::loop(){
    // magnet should be on for predecided time period (PDTD)
    // it should not turn on before at least 1 second has passed from previous off

    if (millis() - prev_time > time_gap){
        prev_time = millis();
        if (!state){
            off();
            time_gap = 1000;
        }
        else{
            if (direction == 0) {
                digitalWrite(first_direction, HIGH);
            }
            if (direction == 1) {
                digitalWrite(second_direction, HIGH);
            }
            time_gap = 5000;
            state = 0; // prepare to turn off after PDTD

        }
    }
}

long TwoWayMagnet::action_start_time{

}
