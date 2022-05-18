/* Interface for a single digital output pin
 * -----------------------------------------
 * @author Tal Eisenberg <eisental@gmail.com>
 */

#include "LineInterface.h"
#include "send.h"

LineInterface::LineInterface(JsonVariant conf)
  : ToggleInterface("line", strdup(conf["name"])) {
  if (!conf.containsKey("pin")) {
    send_error("Missing 'pin' key in line config");
    pin = -1;
    return;
  }
  
  if (!conf["pin"].is<int>()) {
    send_error("'pin' value should be an integer");
    pin = -1;
    return;
  }
  
  if (conf.containsKey("reverse")) {
    if (!conf["reverse"].is<bool>()) {
      send_error("'reverse' value should be a boolean");
      reverse = false;
    }
    reverse = conf["reverse"].as<bool>();
  }
  else {
    reverse = false;
  }
    
  pin = conf["pin"].as<int>();
  pinMode(pin, OUTPUT);
  digitalWrite(pin, reverse ? HIGH : LOW);
}

void LineInterface::value_changed() {
  if (pin < 0) {
    send_error("Can't write value. Pin index is undefined.");
    return;
  }
  digitalWrite(pin, value == 0 ? (reverse ? HIGH : LOW) : (reverse ? LOW : HIGH));
}
