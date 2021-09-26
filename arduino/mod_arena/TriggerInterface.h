#ifndef TriggerInterface_h
#define TriggerInterface_h

#include "Arduino.h"
#include <ArduinoJson.h>
#include "Interface.h"
#include "ToggleInterface.h"

class TriggerInterface: public ToggleInterface {
 public:
  TriggerInterface(JsonVariant conf);

  void loop();
  void set_value(int v);

 private:
  int pin;
  unsigned long high_delay;
  unsigned long low_delay;
  unsigned long cur_ttl;
  bool serial_trigger;
};

#endif
