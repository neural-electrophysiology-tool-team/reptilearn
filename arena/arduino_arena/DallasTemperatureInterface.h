/* Interface for Dallas Temperature devices such as DS18B20
 * --------------------------------------------------------
 * @author Tal Eisenberg <eisental@gmail.com>
 */

#ifndef DallasTemperatureInterface_h
#define DallasTemperatureInterface_h

#include <OneWire.h>
#include <DallasTemperature.h>
#include "send.h"
#include "Interface.h"

class DallasTemperatureInterface: public Interface {
 public:
  DallasTemperatureInterface(JsonVariant conf);
  
  void run(JsonArray cmd);  
  void get_value(JsonDocument* container);  
  void loop();
  
 private:
  OneWire* oneWire = nullptr;
  DallasTemperature* dt = nullptr;
  uint8_t sensor_count;
};

#endif
