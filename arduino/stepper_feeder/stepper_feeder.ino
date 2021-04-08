#include <AccelStepper.h>

const int motor1 = 0;
const int motor2 = 1;
const int motor3 = 2;
const int motor4 = 3;

const int buttonPin = 6;

const int motor_interface_type = 8;

const int STEPPER_SPEED = 500; // maybe works

enum State { 
  standby, // ready for next feeding.
  forward, // move to next cell.
  full_backward, // make sure we are at the stop point on boot.
  short_backward, // after moving forward we need to go back to the stop point.
  prepare // prepare to move forward to the next cell (prevent the reward delay).
};

State state = prepare;

AccelStepper stepper = AccelStepper(motor_interface_type, motor1, motor3, motor2, motor4);

void feed() {
  if (state == standby) {
    state = forward;     
    stepper.setSpeed(STEPPER_SPEED);
  }
}

void setup() {
  stepper.setMaxSpeed(1000);
  Serial.begin(115200);   

  pinMode(buttonPin, INPUT);

  state = full_backward;
  stepper.setCurrentPosition(0);
  stepper.setSpeed(-STEPPER_SPEED);
}

void loop() {
  if (digitalRead(buttonPin) == LOW) {
    feed();
  }
  
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
