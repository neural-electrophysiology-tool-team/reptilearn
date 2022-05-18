/* Interface for controlling a multiplexer such as CD74HC4067 as an output
 * -----------------------------------------------------------------------
 * @author Tal Eisenberg <eisental@gmail.com>
 */

#include "MuxInterface.h"
#include "send.h"

MuxInterface::MuxInterface(JsonVariant conf)
  : ToggleInterface("mux", strdup(conf["name"])) {
  if (!conf.containsKey("signal_pin")) {
    send_error("Missing 'signal_pin' key in mux config");
    signal_pin = -1;
  } else {
    if (!conf["signal_pin"].is<int>()) {
      send_error("'signal_pin' value should be an integer");
      signal_pin = -1;
    }
    else {
      signal_pin = conf["signal_pin"].as<int>();
      pinMode(signal_pin, OUTPUT);
      digitalWrite(signal_pin, LOW);
    }
  }
  
  if (conf.containsKey("enable_pin")) {
    if (!conf["enable_pin"].is<int>()) {
      send_error("'enable_pin' value should be an integer");
      enable_pin = -1;
    }
    else {
      enable_pin = conf["enable_pin"].as<int>();
      pinMode(enable_pin, OUTPUT);
      digitalWrite(enable_pin, LOW);
    }
  } else {
    enable_pin = -1;
  }

  if (conf.containsKey("control_pins")) {
    if (!conf["control_pins"].is<JsonArray>()) {
      send_error("'control_pins' value should be an array");
      control_pins = nullptr;      
    }
    else {
      control_pins = conf["control_pins"];
      JsonArray pins = control_pins.as<JsonArray>();
      for (JsonVariant v : pins) {
	if (!v.is<int>()) {
	  send_error("Invalid 'control_pins' element value. Expecting an integer.");
	  control_pins = nullptr;
	  break;
	}
	
	int pin = v.as<int>();
	pinMode(pin, OUTPUT);
	digitalWrite(pin, LOW);
      }

    }
  } else {
    send_error("Missing 'control_pins' key in mux config");
    control_pins = nullptr;
  }
}

void MuxInterface::value_changed() {
  if (signal_pin < 0) {
    send_error("Can't write value. Signal pin index is undefined.");
    return;
  }

  digitalWrite(signal_pin, value == 0 ? LOW : HIGH);
}

void MuxInterface::run(JsonArray cmd) {
  if (cmd[0] == "set_channel") {
    if (control_pins == nullptr) {
      send_error("Can't change channel. 'control_pins' config key is undefined.");
      return;
    }
    
    if (cmd.size() < 3) {
      send_error("Missing channel value");
      return;
    }

    if (!cmd[2].is<int>()) {
      send_error("Invalid channel value");
      return;
    }

    int c = cmd[2].as<int>();
    set_channel(c);
  } else if (cmd[0] == "set_enable") {
    if (enable_pin < 0) {
      send_error("Can't set enable value. 'enable_pin' config key is undefined.");
      return;
    }
    
    if (cmd.size() < 3) {
      send_error("Missing enable value");
      return;
    }

    if (!cmd[2].is<int>()) {
      send_error("Invalid enable value");
      return;
    }

    int c = cmd[2].as<int>();
    set_enable(c);

  } else {
    ToggleInterface::run(cmd);
  }
  
}

void MuxInterface::set_channel(int channel) {
  JsonArray pins = control_pins.as<JsonArray>();
  int shift = 0;
  char schan[5];
  itoa(channel, schan, 10);

  for (JsonVariant v : pins) {
    int pin = v.as<int>();
    char sval[5];
    digitalWrite(pin, (channel & (1 << shift)) > 0 ? HIGH : LOW);
    shift += 1;
  }
}

void MuxInterface::set_enable(int enable) {
  digitalWrite(enable_pin, enable == 0 ? LOW : HIGH);
}

// TODO: add control_pins in constructor and command to set the current channel
//       requires int to binary conversion.
// TODO: also need to add this to the main file as an optional interface
