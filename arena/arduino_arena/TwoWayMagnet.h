#ifndef DCDoor_h
#define DCDoor_h

#include "Arduino.h"
#include "Interface.h"
#include <ArduinoJson.h>

class TwoWayMagnet : public Interface {
    public:
        TwoWayMagnet(JsonObject conf);

        int state;
        int first_direction_pin;
        int second_direction_pin;

        unsigned long prev_time;
        unsigned long time_gap;

        void loop();
        void run(JsonArray cmd);
        void off();
        void action_start_time();
        void get_value();
};

#endif