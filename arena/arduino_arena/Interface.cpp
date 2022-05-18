/* Abstract class for a hardware interface
 * ---------------------------------------
 * @author Tal Eisenberg <eisental@gmail.com>
 */

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

void Interface::send_info(const char* msg) {
  char topic[64];
  sprintf(topic, "info/%s", get_name());
  send_message(topic, msg);
}

void Interface::send_error(const char* msg) {
  char topic[64];
  sprintf(topic, "error/%s", get_name());
  send_message(topic, msg);
}

void Interface::send_debug(const char* msg) {
  char topic[64];
  sprintf(topic, "debug/%s", get_name());
  send_message(topic, msg);
}
