#include "LineInterface.h"
#include "send.h"

LineInterface::LineInterface(JsonVariant conf)
  : ToggleInterface("line", strdup(conf["name"])) {
  if (!conf.containsKey("pin")) {
    send_message("error/line", "Missing 'pin' key in line config");
    pin = -1;
    return;
  }
  
  if (!conf["pin"].is<int>()) {
    send_message("error/line", "'pin' value should be an integer");
    pin = -1;
    return;
  }
  
  pin = conf["pin"].as<int>();
    pinMode(pin, OUTPUT);
    digitalWrite(pin, LOW);
}

void LineInterface::set_value(int v) {
  value = v;
  if (pin < 0) {
    send_message("error/line", "Can't write value. Pin index is undefined.");
    return;
  }
  digitalWrite(pin, v == 0 ? LOW : HIGH);
}

void LineInterface::loop() {}
