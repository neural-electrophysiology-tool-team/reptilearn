#include <Servo.h> 

Servo myservo;

#define SensorPin A0
#define MasterPin 3
#define ServoPin 9

String cmd;
String instring;
int inint;
int sensorvalue=0;
int pr=0;
int threshold=30;

int start_spin = 0;
int wait_to_end = 1;
int wait_for_cmd = 2;
int flag=0;
int counter_flag=0;
int prev_read = 0;
int feeding_cells=0;

String getValue(String data, char separator, int index)
{
    int found = 0;
    int strIndex[] = { 0, -1 };
    int maxIndex = data.length() - 1;

    for (int i = 0; i <= maxIndex && found <= index; i++) {
        if (data.charAt(i) == separator || i == maxIndex) {
            found++;
            strIndex[0] = strIndex[1] + 1;
            strIndex[1] = (i == maxIndex) ? i+1 : i;
        }
    }
    return found > index ? data.substring(strIndex[0], strIndex[1]) : "";
}



void setup() {
  Serial.begin(9600); // debuggig, instead of master interrupt

  myservo.attach(ServoPin);
  myservo.write(90); //set the servo to no movement
  
  //pinMode(SensorPin, INPUT_PULLUP);
  //pinMode(MasterPin, INPUT_PULLUP);
  //attachInterrupt(digitalPinToInterrupt(MasterPin),start_servo,RISING);
  //attachInterrupt(digitalPinToInterrupt(SensorPin),stop_servo,RISING);
}

void loop() {
  sensorvalue=analogRead(SensorPin);
  if(Serial.available())
  {
    cmd = Serial.readStringUntil('\n');
    if (cmd.startsWith("spin"))
    {
      instring = getValue(cmd, ' ', 1);
      inint=instring.toInt();
      myservo.write(inint);
    }
    else if (cmd.equals("stop"))
    {
      stop_servo();
    }
    else if (cmd.startsWith("sens"))
    {
      instring = getValue(cmd, ' ', 1);
      inint=instring.toInt();
      threshold = inint;
    }
    else if (cmd.startsWith("res"))
    {
      prev_read = 0;
      counter_flag = 0;
      feeding_cells = 0;
    }
  }
  if (prev_read>sensorvalue+100)
  {
    flag=1;
  }
  if (sensorvalue<threshold && flag == 1)
  {
    if(feeding_cells>=19)
    {
      counter_flag=+1;
      if(counter_flag==2)
      {
        counter_flag=0;
        stop_servo();
      }
      flag =0;
    }
    else
    {
    stop_servo();
    flag=0;
    counter_flag=0;
    }
  }
  if (pr%3000==0)
  {
    delay(2);
  }
  prev_read = sensorvalue;
}

void stop_servo()
{
  myservo.write(90);
}


void start_servo()
{
  myservo.write(90);
}
