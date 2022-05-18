/* Send JSON and string messages over the serial port
 * --------------------------------------------------
 * @author Tal Eisenberg <eisental@gmail.com>
 */

#ifndef send_h
#define send_h

#include <ArduinoJson.h>

void send_message(const char* topic, const char* payload);
void send_json(const char* topic, JsonDocument* doc);

#endif send_h
