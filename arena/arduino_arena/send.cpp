/* Send JSON and string messages over the serial port
 * --------------------------------------------------
 * @author Tal Eisenberg <eisental@gmail.com>
 */

#include "send.h"

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
