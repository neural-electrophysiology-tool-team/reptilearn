#include "send.h"
#include "DallasTemperatureInterface.h"

DallasTemperatureInterface::DallasTemperatureInterface(JsonVariant conf)
  : Interface("dallas_temperature", strdup(conf["name"])) {
  
  if (!conf.containsKey("pin")) {
    send_message("error/dallas_temperature", "Missing 'pin' key in config");
    return;
  }
  
  if (!conf["pin"].is<int>()) {
    send_message("error/dallas_temperature", "'pin' value should be an integer");
    return;
  }
  
  int pin = conf["pin"].as<int>();
  
  oneWire = new OneWire(pin);
  dt = new DallasTemperature(oneWire);
  delay(100);
  dt->begin();
  sensor_count = dt->getDeviceCount();
  
  char msg[40];
  sprintf(msg, "Found %u sensors", sensor_count);
  send_message("info/dallas_temperature", msg);
}  

void DallasTemperatureInterface::run(JsonArray cmd) {
  if (cmd[0] == "get") {
    serializeValue();
  }
  else {
    send_message("error/dallas_temperature", "Unknown command");
  }
}

void DallasTemperatureInterface::get_value(JsonDocument* container) {
  JsonArray temps = container->to<JsonArray>();
  
  dt->requestTemperatures();
  
  for (int i=0; i<sensor_count; i++) {
    float temp = dt->getTempCByIndex(i);
    unsigned long t0 = millis();
    while (temp == DEVICE_DISCONNECTED_C && millis() - t0 < 2000);
    
    if (temp != DEVICE_DISCONNECTED_C) {
      temps.add(temp);
    }
    else {
      send_message("error/dallas_temperature", "Device disconnected");
      temps.add(nullptr);
    }
  }
}

void DallasTemperatureInterface::loop() {
}
