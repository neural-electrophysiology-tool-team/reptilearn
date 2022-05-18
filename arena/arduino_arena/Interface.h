/* Abstract class for a hardware interface
 * ---------------------------------------
 * @author Tal Eisenberg <eisental@gmail.com>
 */

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

  void send_info(const char* msg);
  void send_error(const char* msg);
  void send_debug(const char* msg);
  
  virtual void get_value(JsonDocument* container);
  virtual void run(JsonArray cmd);
  virtual void loop();
  
 private:
  char *name;
  char *type;
};

#endif
