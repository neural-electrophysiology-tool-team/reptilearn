/*
Arduino routine to control Servo, DS18B20 temprature sensor, Si7021 humidity sensor, lights through relay,
LED and feeder.
The program awaits a serial command in the following syntax : <cmd> <val0> <val1>
Author: Or Pardilov, 2021
*/
#include <OneWire.h>
#include <DallasTemperature.h>
#include "Adafruit_Si7021.h"
#include <SerialCommands.h>
#include <AccelStepper.h>

// Strart of Stepper feeder setup section
const int motor1 = 10;
const int motor2 = 9;
const int motor3 = 8;
const int motor4 = 7;
const int motor_interface_type = 8;
const int STEPPER_SPEED = 500;

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

// end of Stepper feeder setup section

// Pin numbers definitions
#define LIGHT_1_PORT 2
#define LED_PORT 4
#define ONE_WIRE_BUS 5
#define FEEDER_PORT 8

#define SIZE_OF_CHAR_ARR 128


OneWire oneWire(ONE_WIRE_BUS); //when the sensors are online
DallasTemperature sensors(&oneWire); //when the sensors are online
Adafruit_Si7021 HT_sensor = Adafruit_Si7021(); // create Adafruit_Si7021 class instance



int temp_sensor_count=0;
char buffer[SIZE_OF_CHAR_ARR];
float temp_sensor_reading;

// init a SerialCommands instance, commands ends with a new line: /n
// commands delimiters are whitespaces
SerialCommands serial_commands(&Serial, buffer, sizeof(buffer), "\n", " ");

//Execute a digital write to a given pin number
void Digital_write(SerialCommands* sender)
{
    int port;int val;
    char* port_ch = sender->Next();
    if (port_ch ==NULL)
        return;
    port = atoi(port_ch);
    char* val_ch = sender->Next();
    if (val_ch ==NULL)
        return;
    val = atoi(val_ch);
    digitalWrite(port,val);
    return;
}

//Turn led on/off
void CtlLed(SerialCommands* sender)
{
    int val;
    char* temp = sender->Next();
    temp = sender->Next();
    if (temp ==NULL)
        return;
    val = atoi(temp);
    digitalWrite(LED_PORT,val);
    return;
}

//Turn lights on/off
void CtlLights(SerialCommands* sender)
{
    int val;
    char* temp = sender->Next();
    temp = sender->Next();
    if (temp ==NULL)
        return;
    val = atoi(temp);
    digitalWrite(LIGHT_1_PORT,val);
    return;
}

//Start motor state machine to send a reward
void InitReward(SerialCommands* sender)
{
    feed();
    return;
}

//Poll temprature and humidity sensors readings
void PollSens(SerialCommands* sender)
{
    sensors.requestTemperatures();
    int i;

    for (i = 0;  i < temp_sensor_count;  i++)
    {
      sender->GetSerial()->print("Sensor_");
      sender->GetSerial()->print(i);
      sender->GetSerial()->print(" : ");
      temp_sensor_reading = sensors.getTempCByIndex(i);
      sender->GetSerial()->print(temp_sensor_reading);
      sender->GetSerial()->print("C;");
    }

    //The following is for checking the Humidity sensor H&T
    sender->GetSerial()->print("Sensor_");
    sender->GetSerial()->print(i+1);
    sender->GetSerial()->print(" : ");
    sender->GetSerial()->print(HT_sensor.readTemperature());
    sender->GetSerial()->print("C;");
    sender->GetSerial()->print("Sensor_");
    sender->GetSerial()->print(i+2);
    sender->GetSerial()->print(" : ");
    sender->GetSerial()->print(HT_sensor.readHumidity());
    sender->GetSerial()->print("H;");
    //End the readline
    sender->GetSerial()->println();
    return;
}


void def_cmd(SerialCommands* sender, const char* cmd)
{
  sender->GetSerial()->print("Unrecognized command (SENS) [");
  sender->GetSerial()->print(cmd);
  sender->GetSerial()->println("]");
}


SerialCommand digi_write("Dig",Digital_write);
SerialCommand control_led("Led",CtlLed);
SerialCommand control_lights("Lights",CtlLights);
SerialCommand init_reward("Reward",InitReward);
SerialCommand sensors_poll("Temppoll",PollSens);

void setup() {
  Serial.begin(115200);
  //LED output definition
  pinMode(LIGHT_1_PORT,OUTPUT);
  pinMode(LED_PORT,OUTPUT);
  pinMode(FEEDER_PORT,OUTPUT);
  digitalWrite(LIGHT_1_PORT,LOW);
  digitalWrite(LED_PORT,LOW);
  digitalWrite(FEEDER_PORT,LOW);

  //starting and checking the dallas temp sensors
  sensors.begin(); //when the sensors are online
  Serial.print("Locating temperature sensors... ");
  temp_sensor_count=sensors.getDeviceCount();
  Serial.print("Found ");
  Serial.print(temp_sensor_count); //Number of dallastemp sensors connected.
  Serial.println(" temprature sensors");

  //starting and checking the humidity sensor
  if (!HT_sensor.begin()) {
    Serial.println("Did not find humidity sensor");
  }
  else
  {
    Serial.println("Found Si7021 humidity sensor ");
  }

  serial_commands.AddCommand(&digi_write);
  serial_commands.AddCommand(&control_led);
  serial_commands.AddCommand(&control_lights);
  serial_commands.AddCommand(&init_reward);
  serial_commands.AddCommand(&sensors_poll);
  serial_commands.SetDefaultHandler(def_cmd);

  //stepper feeder setup
  stepper.setMaxSpeed(1000);
  state = full_backward;
  stepper.setCurrentPosition(0);
  stepper.setSpeed(-STEPPER_SPEED);
 }

void loop() {
    //read serial command
    serial_commands.ReadSerial();

    //stepper feeder state machine
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
