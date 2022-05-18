/* Interface for sending periodic pulses over a single digital pin
 * ---------------------------------------------------------------
 * @author Tal Eisenberg <eisental@gmail.com>
 */

#include "TriggerInterface.h"
#include "send.h"

unsigned long maxUnsignedLong = 0UL - 1UL;

TriggerInterface::TriggerInterface(JsonVariant conf)
  : ToggleInterface("trigger", strdup(conf["name"]))
  , count(0)
  , pin_state(LOW) {

  if (!conf.containsKey("pin")) {
    send_error("Missing 'pin' key in config");
    return;
  }
  if (!conf["pin"].is<int>()) {
    send_error("pin: Expecting an integer");
    return;
  }

  if (!conf.containsKey("pulse_len")) {
    send_error("Missing 'pulse_len' key in config");
    return;
  }
  if (!conf["pulse_len"].is<int>()) {
    send_error("pulse_len: Expecting an integer value");
    return;
  }

    if (!conf.containsKey("pulse_width")) {
    send_error("Missing 'pulse_width' key in config");
    return;
  }
  if (!conf["pulse_width"].is<float>()) {
    send_error("pulse_width: Expecting a float value");
    return;
  }

  pin = conf["pin"].as<int>();
  
  pinMode(pin, OUTPUT);
  digitalWrite(pin, pin_state);
  
  // setup trigger delays
  int pulse_len = conf["pulse_len"].as<int>();
  float pulse_width = conf["pulse_width"].as<float>();
  
  high_dur = ceil(pulse_len * pulse_width) * 1000UL;
  low_dur = floor(pulse_len * (1 - pulse_width)) * 1000UL;

  if (!conf.containsKey("serial_trigger")) {
    serial_trigger = false;
  }
  else {    
    if (!conf["serial_trigger"].is<bool>()) {
      send_error("serial_trigger: Expecting a boolean value");
      return;
    }
    serial_trigger = conf["serial_trigger"].as<bool>();
  }

  char msg[40];
  sprintf(msg, "Intialized pulse trigger. high: %lums low: %lums", high_dur / 1000UL, low_dur / 1000UL);
  send_info(msg);
}

void TriggerInterface::loop() {
  if (value == 1) {
    unsigned long t = micros();
    unsigned long dt = t - prev_trans_time;
    if (dt < 0) {
      dt += maxUnsignedLong - prev_trans_time;
    }

    if (pin_state == LOW) {
      if (dt >= low_dur) {
	pin_state = HIGH;
	prev_trans_time = t;
	digitalWrite(pin, pin_state);

	if (serial_trigger) {
	  char msg[40];
	  sprintf(msg, "%lu: HIGH, dt=%luμs", count, dt); 
	  send_info(msg);
	  
	  count += 1;
	}
      }      
    }
    else {
      if (dt >= high_dur) {
	pin_state = LOW;
	prev_trans_time = t;
	digitalWrite(pin, pin_state);
	
	if (serial_trigger) {
	  char msg[40];
	  sprintf(msg, "%lu: LOW, dt=%luμs", count, dt); 
	  send_info(msg);
	}	
      }
    }
  }
}

void TriggerInterface::value_changed() {
  if (value == 1) {
    // start
    send_debug("Starting");
    prev_trans_time = micros();    
  }
  else {
    // stop
    send_debug("Stopping");
    count = 0;
  }
}
