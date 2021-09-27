#include <ArduinoJson.h>
#include "send.h"
#include "Feeder.h"
#include "Interface.h"
#include "LineInterface.h"
#include "TriggerInterface.h"
#include "FeederInterface.h"
#include "DallasTemperatureInterface.h"

static const int MAX_INTERFACES = 32;

Interface *interfaces[MAX_INTERFACES];
int num_interfaces = 0;

void setup() {
  Serial.begin(115200);

  while (!Serial) continue;
  send_message("status", "Waiting for configuration...");
}

void loop() {
  if (Serial.available() > 0) {
    StaticJsonDocument<2048> json;  
    DeserializationError error = deserializeJson(json, Serial);

    switch (error.code()) {
    case DeserializationError::Ok:
      break;
    case DeserializationError::EmptyInput:
      return;
    case DeserializationError::IncompleteInput: // could use a string builder for these 3.
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
      char msg[40];
      sprintf(msg, "Invalid json root type: %s", strdup(json.as<char const*>()));
      send_message("error/parse_json", msg);
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
}

void load_config(JsonObject conf) {
  if (num_interfaces > 0) {
    send_message("error/load_config", "Already configured, reset device to reconfigure.");
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
  send_message("info/load_config", msg);
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
  char msg[40];
  sprintf(msg, "Initializing '%s' (%s)", name, type);
  send_message("info/load_config", msg);

  Interface* ifs;
  
  if (conf["type"] == "feeder") {
    ifs = new FeederInterface(conf);
  }
  else if (conf["type"] == "line") {
    ifs = new LineInterface(conf);
  }
  else if (conf["type"] == "dallas_temperature") {
    ifs = new DallasTemperatureInterface(conf);
  }
  else if (conf["type"] == "trigger") {
    ifs = new TriggerInterface(conf);
  }
  else {
    send_message("error/load_config", "Invalid interface type");
    free(name);
    free(type);
    return;
  }

  add_interface(ifs);
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
    send_message("error/run_command", "Can't run command before loading configuration");
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
  
  const char* ifs_name = strdup(c[1].as<const char*>());

  for (int i=0; i<num_interfaces; i++) {    
    if (strcmp(interfaces[i]->get_name(), ifs_name) == 0) {
      interfaces[i]->run(c);
      return;
    }
  }

  char msg[128];
  sprintf(msg, "Unknown interface: %s", ifs_name);
  send_message("error/run_command", msg);

  free(ifs_name);
}
