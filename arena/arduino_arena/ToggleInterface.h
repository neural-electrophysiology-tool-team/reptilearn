/* Abstract interface for a toggleable device
 * ------------------------------------------
 * @author Tal Eisenberg <eisental@gmail.com>
 */

#ifndef ToggleInterface_h
#define ToggleInterface_h

#include "Arduino.h"
#include <ArduinoJson.h>
#include "Interface.h"

class ToggleInterface: public Interface {
 public:
  ToggleInterface(const char* type, const char* name);  

  virtual void value_changed();
  
  void set_value(int v);
  void get_value(JsonDocument* container);
  void toggle();
  void start_periodic(unsigned long dur);
  void stop_periodic();
  void run(JsonArray cmd);
  void loop();
  
 protected:
  int value;
  
  int periodic_on;
  unsigned long prev_period_toggle;
  unsigned long period_dur;
};

#endif
