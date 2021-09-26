#include "Interface.h"
#include "send.h"

Interface::Interface(const char* type, const char* name)
  : name(name)
  , type(type) {
}

char* Interface::get_type() {
  return type;
}

char* Interface::get_name() {
  return name;
}

void Interface::serializeValue() {
    StaticJsonDocument<200> val_doc;
    get_value(&val_doc);
    StaticJsonDocument<512> doc;
    doc[get_name()] = val_doc;
    send_json("value", &doc);
}
