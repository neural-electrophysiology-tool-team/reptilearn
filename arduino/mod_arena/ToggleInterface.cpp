#include "ToggleInterface.h"
#include "send.h"

ToggleInterface::ToggleInterface(const char* type, const char* name)
  : Interface(type, name),
    value(0) {
}

void ToggleInterface::get_value(JsonDocument* container) {
  container->set(value);
}

void ToggleInterface::toggle() {
  set_value(!value);
}

void ToggleInterface::run(JsonArray cmd) {
  if (cmd[0] == "get") {
    serializeValue();
  }
  else if (cmd[0] == "toggle") {
    toggle();
  }
  else if (cmd[0] == "set") {
    if (cmd.size() < 3) {
      send_message("error/toggle", "Missing set value");
      return;
    }
    
    if (!cmd[2].is<int>()) {
      send_message("error/toggle", "Invalid set value");
      return;
    }
    
    int v = cmd[2].as<int>();
    set_value(v);
  }
  else {
    send_message("error/toggle", "Unknown command");
  }
}

