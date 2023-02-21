/* ReptiLearn Arena Arduino Code
 * -----------------------------
 * @author Tal Eisenberg
 * 
 * This Arduino code can be used to control various hardware components through the ReptiLearn MQTT-Serial bridge. 
 * After uploading the code to any number of Arduino microprocessors, each Arduino can be configured with different 
 * functionality using a single JSON file.
 * 
 * Required Arduino libraries:
 * - ArduinoJson
 * - DallasTemperature
 * - OneWire
 * - AccelStepper
 */

#include <ArduinoJson.h>
#include "send.h"
#include "Interface.h"

// To remove any unused interface type, simply comment its include line below:
#include "LineInterface.h"
#include "TriggerInterface.h"
#include "FeederInterface.h"
#include "DallasTemperatureInterface.h"
#include "MuxInterface.h"

static const int MAX_INTERFACES = 32;

Interface *interfaces[MAX_INTERFACES];
int num_interfaces = 0;
unsigned long last_config_request_time = 0;

void setup() {
  Serial.begin(115200);

  while (!Serial) continue;
  request_configuration();
}

void loop() {
  if (num_interfaces == 0 && (millis() - last_config_request_time > 5000)) {
    request_configuration();
  }
  
  if (Serial.available() > 0) {
    StaticJsonDocument<2048> json;  
    DeserializationError error = deserializeJson(json, Serial);

    switch (error.code()) {
    case DeserializationError::Ok:
      break;
    case DeserializationError::EmptyInput:
      return;
    case DeserializationError::IncompleteInput:
    case DeserializationError::InvalidInput:
    case DeserializationError::NoMemory:
    default:
      send_message("error/parse_json", error.c_str());
      return;
    }
     
    if (json.is<JsonObject>()) {
      load_config(json.as<JsonObject>());
    }
    else if (json.is<JsonArray>()) {
      run_command(json.as<JsonArray>());
    }
    else {
      send_message("error/parse_json", "Expecting json root to be an array or an object.");
    }
  }

  for (int i=0; i<num_interfaces; i++) {
    interfaces[i]->loop();
  }
}

void run_all(JsonArray cmd) {
  if (cmd[0] == "get") {
    StaticJsonDocument<1024> doc;
    JsonObject container = doc.to<JsonObject>();
    for (int i=0; i<num_interfaces; i++) {
      StaticJsonDocument<512> ifs_doc;
      Interface* ifs = interfaces[i];
      ifs->get_value(&ifs_doc);
      if (ifs_doc != nullptr) {
	doc[ifs->get_name()] = ifs_doc;
      }      
    }
    send_json("all_values", &doc);
  }
  else {
    send_message("error/run_all", "Unknown command");
  }
}

void request_configuration() {
  send_message("status", "Waiting for configuration...");  
  last_config_request_time = millis();
}

void load_config(JsonObject conf) {
  if (num_interfaces > 0) {
    send_message("error/load_config", "Port is already configured, reset the device and try again.");
    return;
  }

  if (conf.size() == 0) {
    send_message("error/load_config", "Empty configuration object.");
    return;
  }

  if (!conf.begin()->value().is<JsonArray>()) {
    send_message("error/load_config", "Expecting first value to be an array.");
    return;
  }

  send_message("info/load_config", "Loading configuration...");

  JsonArray ifs_conf = conf.begin()->value().as<JsonArray>();  
  
  for (JsonVariant v : ifs_conf) {
    if (!v.is<JsonObject>()) {
      send_message("error/load_config", "Expecting interface array element to be an object");
      return;
    }

    JsonObject ifs_conf = v.as<JsonObject>();
    parse_interface_config(ifs_conf);
  }
  char msg[40];

  sprintf(msg, "Initialized %d interfaces", num_interfaces);
  send_message("info/config_loaded", msg);
}

void parse_interface_config(JsonObject conf) {
  if (!conf.containsKey("type")) {
    send_message("error/load_config", "Missing type key in interface config");
    return;
  }
  if (!conf.containsKey("name")) {
    send_message("error/load_config", "Missing name key in interface config");
    return;
  }

  char* name = strdup(conf["name"].as<const char*>());
  char* type =  strdup(conf["type"].as<const char*>());
  char msg[64];
  sprintf(msg, "Initializing '%s' (%s)", name, type);
  send_message("info/load_config", msg);
  free(name);
  free(type);
  
  #ifdef FeederInterface_h
  if (conf["type"] == "feeder") {
    add_interface(new FeederInterface(conf));
    return;
  }
  #endif

  #ifdef LineInterface_h
  if (conf["type"] == "line") {
    add_interface(new LineInterface(conf));
    return;
  }
  #endif

  #ifdef DallasTemperatureInterface_h
  if (conf["type"] == "dallas_temperature") {
    add_interface(new DallasTemperatureInterface(conf));
    return;
  }
  #endif

  #ifdef TriggerInterface_h
  if (conf["type"] == "trigger") {
    add_interface(new TriggerInterface(conf));
    return;
  }
  #endif

  #ifdef MuxInterface_h
  if (conf["type"] == "mux") {
    add_interface(new MuxInterface(conf));
    return;
  }
  #endif

  name = strdup(conf["name"].as<const char*>());
  type =  strdup(conf["type"].as<const char*>());
  char umsg[128];
  sprintf(umsg, "Unknown interface type '%s' in interface '%s'", type, name); 
  send_message("error/load_config", umsg);
  free(name);
  free(type);
}

void add_interface(Interface* i) {
  if (num_interfaces >= MAX_INTERFACES) {
    send_message("error/load_config", "Too many interfaces are defined");
    return;
  }
  interfaces[num_interfaces] = i;
  num_interfaces += 1;
}

void run_command(JsonArray c) {
  if (num_interfaces == 0) {
    send_message("error/run_command", "Can't run command. There are no configured interfaces.");
    return;
  }
  if (c.size() < 2) {
    send_message("error/run_command", "Invalid command");
    return;
  }
  if (!c[0].is<const char*>() || !c[1].is<const char*>()) {
    send_message("error/run_command", "Invalid command name or interface");
    return;
  }
  
  if (c[1] == "all") {
    run_all(c);
    return;
  }

  for (int i=0; i<num_interfaces; i++) {    
    if (interfaces[i]->get_name() == c[1]) {
      interfaces[i]->run(c);
      return;
    }
  }

  char msg[128];
  const char* ifs_name = strdup(c[1].as<const char*>());
  sprintf(msg, "Unknown interface: %s", ifs_name);
  send_message("error/run_command", msg);
  free(ifs_name);
}
