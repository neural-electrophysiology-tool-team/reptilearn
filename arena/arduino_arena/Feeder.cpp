/* Arduino library for controlling a fish feeder (EVNICE EV200GW or similar).
 * --------------------------------------------------------------------------
 * @author Tal Eisenberg <eisental@gmail.com>
 */


#include "Arduino.h"
#include "Feeder.h"

Feeder::Feeder(int motor1, int motor2, int motor3, int motor4) :
  stepper(AccelStepper(MOTOR_INTERFACE_TYPE, motor1, motor3, motor2, motor4)),
  state(full_backward)
{
}

void Feeder::init() {
  state = full_backward;
  stepper.setMaxSpeed(1000);
  stepper.setCurrentPosition(0);
  stepper.setSpeed(-STEPPER_SPEED);
}

void Feeder::loop() {
  if (state == forward) {
    if (stepper.currentPosition() != 5096) {
      stepper.runSpeed();
    }
    else {
      state = short_backward;
      stepper.setSpeed(-STEPPER_SPEED);
    }
  }
  else if (state == short_backward) {
    if (stepper.currentPosition() != 3000) {
      stepper.runSpeed();
    }
    else {
      state = prepare;
      stepper.setCurrentPosition(0);
      stepper.setSpeed(STEPPER_SPEED);
    }
  }
  else if (state == prepare) {
    if (stepper.currentPosition() != 4000) {
      stepper.runSpeed();
    }
    else {
      state = standby;
    }
  }
  else if (state == full_backward) {
    if (stepper.currentPosition() != -4096) {
      stepper.runSpeed();
    }
    else {
      state = prepare;
      stepper.setCurrentPosition(0);
      stepper.setSpeed(STEPPER_SPEED);      
    } 
  }
}

void Feeder::feed() {
  if (state == standby) {
    state = forward;     
    stepper.setSpeed(STEPPER_SPEED);
  }
}
