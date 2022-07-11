/* Interface for the EVNICE feeder library
 * ---------------------------------------
 * @author Tal Eisenberg <eisental@gmail.com>
 */

#include "FeederInterface.h"

FeederInterface::FeederInterface(JsonObject conf)
  : Interface("feeder", strdup(conf["name"].as<const char*>())) {
  if (!conf.containsKey("pins")) {
    send_error("Missing 'pins' key in config");
    feeder = nullptr;
    return;
  }
  if (!conf["pins"].is<JsonArray>()) {
    send_error("Invalid 'pins' value");
    feeder = nullptr;
    return;
  }
  
  JsonArray pins = conf["pins"].as<JsonArray>();
  
  if (pins.size() != 4) {
    send_error("pins: Expecting exactly 4 pin indices");
    feeder = nullptr;
    return;
  }
  for (int i = 0; i < pins.size(); i++) {
    if (!pins[i].is<int>()) {
      send_error("pins: Each element should be an integer");
      feeder = nullptr;
      return;
    }
  }
  feeder = new Feeder(pins[0].as<int>(), pins[1].as<int>(), pins[2].as<int>(), pins[3].as<int>());
  feeder->init();
}

void FeederInterface::get_value(JsonDocument* container) {
  container->set(nullptr);
}
  
void FeederInterface::run(JsonArray cmd) {
  if (cmd[0] == "dispense") {
    // possibly add a check for time between consecutive rewards
    if (feeder != nullptr) {
      send_info("Dispensing reward");
      feeder->feed();
    }
    last_reward = millis();
  }
  else {
    send_error("Unknown command");
  }
}

void FeederInterface::loop() {
  feeder->loop();
}
