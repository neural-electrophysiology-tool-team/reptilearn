
#ifndef DCDoor_h
#define DCDoor_h

#include "Arduino.h"
#include "Interface.h"
#include <ArduinoJson.h>


const int CLOSE_TIME = 700;
const int OPEN_TIME = 1300;

enum DoorState {
    closed,
    opened,
    closing,
    opening,
};

class DCDoor : public Interface {
    public:
        DCDoor(JsonObject conf);
        DoorState state;
        int closing_pin;
        int opening_pin;
        void init();
        void close();
        void open();
        void get_value(JsonDocument* container);
        void run(JsonArray cmd);
        void loop();
        long action_start_time;
};

#endif