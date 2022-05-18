/* Interface for controlling a multiplexer such as CD74HC4067 as an output
 * -----------------------------------------------------------------------
 * @author Tal Eisenberg <eisental@gmail.com>
 */

#ifndef MuxInterface_h
#define MuxInterface_h

#include "Arduino.h"
#include <ArduinoJson.h>
#include "ToggleInterface.h"

class MuxInterface: public ToggleInterface {
 public:
  MuxInterface(JsonVariant conf);

  void value_changed();
  void run(JsonArray cmd);
  void set_channel(int channel);
  void set_enable(int enable);
  
 private:
  int signal_pin;
  int enable_pin;
  StaticJsonDocument<128> control_pins;
};

#endif
