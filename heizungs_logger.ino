
/*
*/

#include <stdint.h>
#include <OneWire.h>
#include <DallasTemperature.h>

#include "firmware/frame.h"


uint8_t FIRST_ONE_WIRE_BUS = 2;
uint8_t ONE_WIRE_PINS = 4;
uint8_t FIRST_INPUT = FIRST_ONE_WIRE_BUS + ONE_WIRE_PINS + 4;
uint8_t INPUT_PINS = 2;
uint8_t HEARTBEAT_PIN = 6;

void setup() {
  Serial.begin(9600);
  while (!Serial) {
    ; // wait for serial port to connect. Needed for Native USB only
  }
  pinMode(FIRST_INPUT, INPUT);
  pinMode(FIRST_INPUT + 1, INPUT);
  pinMode(HEARTBEAT_PIN, OUTPUT);
  
  //Serial.println("Setup");  
}


void loop() {
  // set 1wire pin
  if(Serial.available() == false)
  {
    return;
  }
  digitalWrite(HEARTBEAT_PIN, HIGH);
  Serial.read();

  float temps[ONE_WIRE_PINS] = {};
  bool inputs[INPUT_PINS] = {};
  
  for(uint8_t offset = 0; offset < ONE_WIRE_PINS; offset++ )
  {
    OneWire oneWire(FIRST_ONE_WIRE_BUS + offset);
    DallasTemperature sensors(&oneWire);
    sensors.requestTemperatures();
    temps[offset] = sensors.getTempCByIndex(0);
  }
  for(uint8_t offset = 0; offset < INPUT_PINS; offset++)
  {
    int inputState = digitalRead(FIRST_INPUT + offset);
    inputs[offset] = inputState == HIGH;
  }

  char frame[128];
  hlog::formatFrame(frame, sizeof(frame), temps, ONE_WIRE_PINS, inputs, INPUT_PINS, 1);
  Serial.print(frame);
  digitalWrite(HEARTBEAT_PIN, LOW);

  // reset
  // skip
  // start conversion 0x44
  // sleep 1 second
  // reset
  // init read 0xbe
  // read 10 bytes 8 byte CRC + 2 bytes raw

  
}