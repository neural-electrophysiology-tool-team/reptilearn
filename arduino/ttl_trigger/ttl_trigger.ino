#include <math.h>

const int TTL_PIN = 12;
float pulse_width = 0.7;
int fps = 60;
float duration = 1.0e6/fps; // in microsecs;
long high_time = ceil(duration * pulse_width);
long low_time = ceil(duration * (1 - pulse_width));

void setup() {
  pinMode(TTL_PIN, OUTPUT);
}

void loop() {
  digitalWrite(TTL_PIN, HIGH);
  delayMicroseconds(high_time);
  digitalWrite(TTL_PIN, LOW);
  delayMicroseconds(low_time);
}
