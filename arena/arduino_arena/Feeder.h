/* Arduino library for controlling a fish feeder (EVNICE EV200GW or similar).
 * --------------------------------------------------------------------------
 * @author Tal Eisenberg <eisental@gmail.com>
 */

#ifndef Feeder_h
#define Feeder_h

#include "Arduino.h"
#include <AccelStepper.h>

const int STEPPER_SPEED = 500;
const int MOTOR_INTERFACE_TYPE = 8;

enum State {
  standby, // ready for next feeding.
  forward, // move to next cell.
  full_backward, // make sure we are at the stop point on boot.
  short_backward, // after moving forward we need to go back to the stop point.
  prepare // prepare to move forward to the next cell (prevent the reward delay).
};

class Feeder {
 public:
  State state;
  AccelStepper stepper;  
  Feeder(int motor1, int motor2, int motor3, int motor4);
  void init();
  void feed();
  void loop();
};

#endif
