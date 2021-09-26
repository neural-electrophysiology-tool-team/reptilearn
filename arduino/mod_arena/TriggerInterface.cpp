#include "TriggerInterface.h"
#include "send.h"

TriggerInterface::TriggerInterface(JsonVariant conf)
  : ToggleInterface("trigger", strdup(conf["name"]))
  , cur_ttl(0){
  // pin, pulse_len, pulse_width, serial_trigger
  if (!conf.containsKey("pin")) {
    send_message("error/trigger", "Missing 'pin' key in config");
    return;
  }
  if (!conf["pin"].is<int>()) {
    send_message("error/trigger", "pin: Expecting an integer");
    return;
  }

  if (!conf.containsKey("pulse_len")) {
    send_message("error/trigger", "Missing 'pulse_len' key in config");
    return;
  }
  if (!conf["pulse_len"].is<int>()) {
    send_message("error/trigger", "pulse_len: Expecting an integer value");
    return;
  }

    if (!conf.containsKey("pulse_width")) {
    send_message("error/trigger", "Missing 'pulse_width' key in config");
    return;
  }
  if (!conf["pulse_width"].is<float>()) {
    send_message("error/trigger", "pulse_width: Expecting a float value");
    return;
  }

  pin = conf["pin"].as<int>();
  pinMode(pin, OUTPUT);
  
  // setup trigger delays
  int pulse_len = conf["pulse_len"].as<int>();
  float pulse_width = conf["pulse_width"].as<float>();
  
  high_delay = ceil(pulse_len * pulse_width);
  low_delay = floor(pulse_len * (1 - pulse_width));

  if (!conf.containsKey("serial_trigger")) {
    serial_trigger = false;
  }
  else {    
    if (!conf["serial_trigger"].is<bool>()) {
      send_message("error/trigger", "serial_trigger: Expecting a boolean value");
      return;
    }
    serial_trigger = conf["serial_trigger"].as<bool>();
  }  
}

void TriggerInterface::loop() {
  if (value == 1) {
    digitalWrite(pin, HIGH);

    unsigned long ser_time = 0; // time it takes to send a trigger through serial in microsecs.
    if (serial_trigger) {
      unsigned long high_time = micros();

      char msg[40];
      sprintf(msg, "%lu: %lu", cur_ttl, high_time); 
      send_message("info/trigger", msg);

      ser_time = floor((micros() - high_time) / 1000);
      cur_ttl += 1;
    }

    if (high_delay - ser_time > 0)
      delay(high_delay - ser_time);

    digitalWrite(pin, LOW);

    delay(low_delay);
  }
}

void TriggerInterface::set_value(int v) {
  if (value == v) return;
  
  value = v;
  if (v == 0) {
    // stop
    cur_ttl = 0;
  }
}
