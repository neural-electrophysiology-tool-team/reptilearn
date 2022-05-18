/* Interface for sending periodic pulses over a single digital pin
 * ---------------------------------------------------------------
 * @author Tal Eisenberg <eisental@gmail.com>
 */

#ifndef TriggerInterface_h
#define TriggerInterface_h

#include "Arduino.h"
#include <ArduinoJson.h>
#include "Interface.h"
#include "ToggleInterface.h"

class TriggerInterface: public ToggleInterface {
 public:
  TriggerInterface(JsonVariant conf);

  void loop();
  void value_changed();

 private:
  int pin;
  unsigned long high_dur;
  unsigned long low_dur;
  bool serial_trigger;
  
  int pin_state;
  unsigned long prev_trans_time;
  unsigned long count;  
};

#endif
