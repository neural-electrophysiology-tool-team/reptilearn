#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <Feeder.h>

void send_message(const char* topic, const char* payload);
void send_json(const char* topic, JsonDocument* doc);

class Interface {
 public:
  Interface(const char* type, const char* name)
    : name(name)
    , type(type) {
  }
  
  char* get_type() {
    return type;
  }
  char* get_name() {
    return name;
  }

  void serializeValue() {
    StaticJsonDocument<200> val_doc;
    get_value(&val_doc);
    StaticJsonDocument<512> doc;
    doc[get_name()] = val_doc;
    send_json("value", &doc);
  }
  
  virtual void get_value(JsonDocument* container);
  virtual void run(JsonArray cmd);
  virtual void loop();
  
 private:
  char *name;
  char *type;
};

class ToggleInterface: public Interface {
 public:
  ToggleInterface(const char* type, const char* name)
    : Interface(type, name),
    value(0) { }
  virtual void set_value(int v);

  void get_value(JsonDocument* container) {
    container->set(value);
  }

  void toggle() {
    set_value(!value);
  }

  void run(JsonArray cmd) {
    if (cmd.size() == 0) {
      send_message("error/toggle", "Empty command array");
      return;
    }
    if (!cmd[0].is<char*>()) {
      send_message("error/toggle", "Non-string command name");
      return;
    }
    
    if (cmd[0] == "get") {
      serializeValue();
    }
    else if (cmd[0] == "set") {
      if (cmd.size() < 3) {
	send_message("error/toggle", "Missing set value");
	return;
      }
      if (!cmd[2].is<int>()) {
	send_message("error/toggle", "Invalid set value");
	return;
      }
      int v = cmd[2].as<int>();
      set_value(v);
    }
    else if (cmd[0] == "toggle") {
      toggle();
    }
    else {
      send_message("error/toggle", "Unknown command");
    }
  }
 protected:
  int value;
};

class LineInterface: public ToggleInterface {
 public:
  LineInterface(JsonVariant conf)
    : ToggleInterface("line", strdup(conf["name"])) {
    if (!conf.containsKey("pin")) {
      send_message("error/line", "Missing 'pin' key in line config");
      pin = -1;
      return;
    }

    if (!conf["pin"].is<int>()) {
      send_message("error/line", "'pin' value should be an integer");
      pin = -1;
      return;
    }
    
    pin = conf["pin"].as<int>();
    pinMode(pin, OUTPUT);
    digitalWrite(pin, LOW);
  }
  
  void set_value(int v) {
    value = v;
    if (pin < 0) {
      send_message("error/line", "Can't write value. Pin index is undefined.");
      return;
    }
    digitalWrite(pin, v == 0 ? LOW : HIGH);
  }

  void loop() {}
  
 private:
  int pin;
};

class FeederInterface: public Interface {
 public:
  FeederInterface(JsonObject conf)
    : Interface("feeder", strdup(conf["name"].as<const char*>())) {
    if (!conf.containsKey("pins")) {
      send_message("error/feeder", "Missing 'pins' key in feeder config");
      feeder = nullptr;
      return;
    }
    if (!conf["pins"].is<JsonArray>()) {
      send_message("error/feeder", "Invalid 'pins' value");
      feeder = nullptr;
      return;
    }
    
    JsonArray pins = conf["pins"].as<JsonArray>();
    
    if (pins.size() != 4) {
      send_message("error/feeder", "pins: Expecting exactly 4 pin indices");
      feeder = nullptr;
      return;
    }
    for (int i = 0; i < pins.size(); i++) {
      if (!pins[i].is<int>()) {
	send_message("error/feeder", "pins: Each element should be an integer");
	feeder = nullptr;
	return;
      }
    }
    feeder = new Feeder(pins[0].as<int>(), pins[1].as<int>(), pins[2].as<int>(), pins[3].as<int>());
    feeder->init();
  }

  void run(JsonArray cmd) {
    if (!cmd[0].is<char*>()) {
      send_message("error/feeder", "Non string command name");
      return;
    }
    
    if (cmd[0] == "dispense") {
      // possibly add a check for time between consecutive rewards
      if (feeder != nullptr) {
	send_message("info/feeder", "Dispensing reward");
	feeder->feed();
      }
      last_reward = millis();
    }
    else {
      send_message("error/feeder", "Unknown command");
    }
  }

  void loop() {
    feeder->loop();
  }

  void get_value(JsonDocument* container) {
    container->set(nullptr);
  }
  
 private:
  Feeder *feeder;
  unsigned long last_reward = -1;
};

class DallasTemperatureInterface: public Interface {
 public:
  DallasTemperatureInterface(JsonVariant conf)
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

  void run(JsonArray cmd) {
    if (cmd[0] == "get") {
      serializeValue();
    }
    else {
      send_message("error/dallas_temperature", "Unknown command");
    }
  }
  
  void get_value(JsonDocument* container) {
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

  void loop() {}
  
 private:
  OneWire* oneWire = nullptr;
  DallasTemperature* dt = nullptr;
  uint8_t sensor_count;
};

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
    send_message("error/load_config", "Already configured. Reset device");
    return;
  }

  if (!conf.containsKey("interfaces")) {
    send_message("error/load_config", "Missing root 'interfaces' key");
    return;
  }
  if (!conf["interfaces"].is<JsonArray>()) {
    send_message("error/load_config", "Expecting 'interfaces' value to be an array");
    return;
  }
  
  send_message("info/load_config", "Loading configuration...");
  
  for (JsonVariant v : conf["interfaces"].as<JsonArray>()) {
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
    send_message("error/add_interface", "Too many interfaces are defined");
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
  
  const char* name = strdup(c[0].as<const char*>());

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

  free(name);
  free(ifs_name);
}

void send_message(const char* topic, const char* payload) {
  Serial.print(topic);
  Serial.print("#");
  Serial.println(payload);
}

void send_json(const char* topic, JsonDocument* doc) {
  Serial.print(topic);
  Serial.print("#");
  serializeJson(*doc, Serial);
  Serial.println();
}
