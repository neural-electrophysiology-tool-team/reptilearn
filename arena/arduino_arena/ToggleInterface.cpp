/* Abstract interface for a toggleable device
 * ------------------------------------------
 * @author Tal Eisenberg <eisental@gmail.com>
 */

#include "ToggleInterface.h"
#include "send.h"

ToggleInterface::ToggleInterface(const char* type, const char* name)
  : Interface(type, name),
    value(0),
    periodic_on(0),
    prev_period_toggle(0),
    period_dur(0) {
}

void ToggleInterface::get_value(JsonDocument* container) {
  container->set(value);
}

void ToggleInterface::set_value(int v) {
  if (value == v) return;
  
  value = v;
  value_changed();
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
      send_error("Missing set value");
      return;
    }
    
    if (!cmd[2].is<int>()) {
      send_error("Invalid set value");
      return;
    }
    
    int v = cmd[2].as<int>();
    set_value(v);
  }
  else if (cmd[0] == "periodic") {
    if (cmd.size() < 3) {
      send_error("Missing periodic start/stop value");
      return;
    }
    if (!cmd[2].is<int>()) {
      send_error("Invalid periodic start/stop value");
      return;
    }

    if (cmd[2] == 0) {
      stop_periodic();
    }
    else {
      if (cmd.size() < 4) {
	send_error("Missing period duration value");
	return;
      }
      if (!cmd[3].is<unsigned long>()) {
	send_error("Invalid period duration value");
	return;
      }
      start_periodic(cmd[3]);
    }
  }
  else {
    send_error("Unknown command");
  }
}

void ToggleInterface::start_periodic(unsigned long dur) {
  if (periodic_on) {
    return;
  }

  periodic_on = 1;
  period_dur = dur;
  prev_period_toggle = millis();
}

void ToggleInterface::stop_periodic() {
  if (!periodic_on) {
    return;
  }

  periodic_on = 0;
  period_dur = 0;
  prev_period_toggle = 0;
  set_value(0);
}

void ToggleInterface::loop() {
  if (periodic_on && period_dur > 0) {
    unsigned long now = millis();
    if (now - prev_period_toggle >= period_dur) {
      prev_period_toggle = now;
      toggle();
    }
  }
}
