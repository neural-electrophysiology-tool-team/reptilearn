#ifndef Interface_h
#define Interface_h

#include "Arduino.h"
#include <ArduinoJson.h>

class Interface {
 public:
  Interface(const char* type, const char* name);
  
  char* get_type();
  char* get_name();

  void serializeValue();  

  virtual void get_value(JsonDocument* container);
  virtual void run(JsonArray cmd);
  virtual void loop();
  
 private:
  char *name;
  char *type;
};

#endif
