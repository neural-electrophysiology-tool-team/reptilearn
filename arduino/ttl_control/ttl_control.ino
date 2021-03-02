#include <SerialCommands.h>
#include <math.h>

/*
 TTL Trigger Arduino Controller 
 author: Tal Eisenberg

 The program accepts commands as string lines over the serial port (each command should
 end with \n).

 Commands:
 - START <pulse len> <pulse width> <ttl count> <serial trigger>
   Starts sending ttl triggers.

   pulse len - total pulse length in ms. default: 17ms
   pulse width - fraction of high duration (0-1). default: 0.7
   ttl count - number of triggers to output. 0 for unlimited. default: 0
   serial trigger - Any value will cause triggers to be sent over serial (for debug purposes). 
 
 - STOP - Stops sending triggers.

 Requires the SerialCommands library:
   https://github.com/ppedro74/Arduino-SerialCommands
*/


const int DEFAULT_PULSE_LEN = 17; // ms
const float DEFAULT_PULSE_WIDTH = 0.7;
const int TTL_PIN = 12;

char serial_buffer[32];

bool running = false;
bool serial_trigger = false;
long high_delay, low_delay; // in millis

// 0 will continue indefinitely, otherwise will stop after this amount of triggers
long ttl_count = 0;
long cur_ttl = 0;

SerialCommands serial_commands(&Serial, serial_buffer, sizeof(serial_buffer), "\n", " ");

void start(int pulse_len, float pulse_width) {
}

void stop() {
  if (!running) return;
  
  cur_ttl = 0;
  serial_trigger = false;
  running = false;

  Serial.println("Stopped running");
}

SerialCommand cmd_stop("STOP", stop);
SerialCommand cmd_start("START", start);


void start(SerialCommands* sender) {
  if (running) return;
  
  int pulse_len;
  float pulse_width;
  
  char* s_pulse_len = sender->Next();
  
  if (s_pulse_len == NULL) {
    pulse_len = DEFAULT_PULSE_LEN;
  }
  else {
    pulse_len = atoi(s_pulse_len);
  }

  char* s_pulse_width = sender->Next();
  if (s_pulse_width == NULL) {
    pulse_width = DEFAULT_PULSE_WIDTH;
  }
  else {
    pulse_width = atof(s_pulse_width);
  }

  char* s_ttl_count = sender->Next();
  if (s_ttl_count != NULL)
    ttl_count = atol(s_ttl_count);
  
  char* do_serial_trigger = sender->Next();
  if (do_serial_trigger != NULL)
    serial_trigger = true;

  // setup trigger delays
  high_delay = ceil(pulse_len * pulse_width);
  low_delay = floor(pulse_len * (1 - pulse_width));

  running = true;

  sender->GetSerial()->print("Running ");
  sender->GetSerial()->print(high_delay);
  sender->GetSerial()->print(", ");
  sender->GetSerial()->print(low_delay);
  sender->GetSerial()->print(", ");
  sender->GetSerial()->print(ttl_count);
  sender->GetSerial()->print(", ");
  sender->GetSerial()->print(serial_trigger);
  sender->GetSerial()->println();
}

//This is the default handler, and gets called when no other command matches.
void cmd_unrecognized(SerialCommands* sender, const char* cmd)
{
  sender->GetSerial()->print("Unrecognized command [");
  sender->GetSerial()->print(cmd);
  sender->GetSerial()->println("]");
}

void setup() {
  pinMode(TTL_PIN, OUTPUT);
  Serial.begin(115200);
  serial_commands.AddCommand(&cmd_stop);
  serial_commands.AddCommand(&cmd_start);
  serial_commands.SetDefaultHandler(cmd_unrecognized);
}

int ser_time = 0; // time it takes to send trigger through serial in microsecs.

void loop() {
  serial_commands.ReadSerial();
  
  if (running) {
    digitalWrite(TTL_PIN, HIGH);

    if (serial_trigger) {
      unsigned long high_time = micros();
      Serial.print(cur_ttl);
      Serial.print(" ");
      Serial.println(high_time);
      ser_time = floor((micros() - high_time) / 1000);
    }

    if (high_delay - ser_time > 0)
      delay(high_delay - ser_time);

    digitalWrite(TTL_PIN, LOW);

    delay(low_delay);

    cur_ttl += 1;

    if (ttl_count > 0 && cur_ttl >= ttl_count) {
      stop();
    }
  }
}
