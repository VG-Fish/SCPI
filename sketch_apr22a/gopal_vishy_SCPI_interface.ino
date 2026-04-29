#define SERIAL_BAUD 115200
#define ADC_VREF 5.0f
#define ADC_BITS 1023.0f

void setPWM(int pin, float volts) {
  volts = constrain(volts, 0.0f, 5.0f);
  int duty = (int)((volts / 5.0f) * 255.0f + 0.5f);
  analogWrite(pin, duty);
}

int getPinFromString(String p) {
  p.trim();
  p.toUpperCase();
  if (p == "A0")
    return A0;
  if (p == "A1")
    return A1;
  if (p == "A2")
    return A2;
  if (p == "A3")
    return A3;
  if (p == "A4")
    return A4;
  if (p == "A5")
    return A5;
  return -1;
}

void setup() { Serial.begin(SERIAL_BAUD); }

void handleCommand(String cmd) {
  cmd.trim();

  if (cmd == "*IDN?") {
    Serial.println("ECE20007,ArduinoSCPI,Superposition,1.0");
  } else if (cmd.startsWith("MEAS:VOLT?")) {
    String args = cmd.substring(10);
    args.trim();

    String result = "";
    int lastIndex = 0;
    int commaIndex = args.indexOf(',');

    while (lastIndex != -1) {
      String pinStr;
      if (commaIndex != -1) {
        pinStr = args.substring(lastIndex, commaIndex);
        lastIndex = commaIndex + 1;
        commaIndex = args.indexOf(',', lastIndex);
      } else {
        pinStr = args.substring(lastIndex);
        lastIndex = -1;
      }

      int pin = getPinFromString(pinStr);
      if (pin != -1) {
        float val = analogRead(pin) * (ADC_VREF / ADC_BITS);
        result += String(val, 4);
      } else {
        result += "NAN";
      }

      if (lastIndex != -1)
        result += ",";
    }
    Serial.println(result);
  } else {
    Serial.println("ERR:UNKNOWN_CMD");
  }
}

void loop() {
  if (Serial.available()) {
    handleCommand(Serial.readStringUntil('\n'));
  }
}
