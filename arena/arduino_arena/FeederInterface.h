/* Interface for the EVNICE feeder library
 * ---------------------------------------
 * @author Tal Eisenberg <eisental@gmail.com>
 */

#ifndef FeederInterface_h
#define FeederInterface_h

#include "Arduino.h"
#include <ArduinoJson.h>
#include "Interface.h"
#include "Feeder.h"

class FeederInterface: public Interface {
 public:
  FeederInterface(JsonObject conf);

  void get_value(JsonDocument* container);  
  void run(JsonArray cmd);
  void loop();
  
 private:
  Feeder *feeder;
  unsigned long last_reward = -1;
};

#endif
