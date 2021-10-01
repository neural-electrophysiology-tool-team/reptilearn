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
  void run(JsonArray cmd);
  
 protected:
  int value;
};

#endif
