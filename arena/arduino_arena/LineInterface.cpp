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
  
  pin = conf["pin"].as<int>();
  pinMode(pin, OUTPUT);
  digitalWrite(pin, LOW);
}

void LineInterface::value_changed() {
  if (pin < 0) {
    send_error("Can't write value. Pin index is undefined.");
    return;
  }
  digitalWrite(pin, value == 0 ? LOW : HIGH);
}
