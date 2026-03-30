#include <Adafruit_NeoPixel.h>
#include <Servo.h>

#define LED_PIN 6
#define NUM_PIXELS 27

Servo leftServo;
Servo rightServo;
Adafruit_NeoPixel strip(NUM_PIXELS, LED_PIN, NEO_GRB + NEO_KHZ800);

const int LEFT_SERVO_PIN = 9;
const int RIGHT_SERVO_PIN = 10;

String inputLine = "";
int currentLeftAngle = 90;
int currentRightAngle = 90;
int currentR = 0;
int currentG = 80;
int currentB = 0;

void setLedColor(int r, int g, int b) {
  currentR = constrain(r, 0, 255);
  currentG = constrain(g, 0, 255);
  currentB = constrain(b, 0, 255);
  uint32_t color = strip.Color(currentR, currentG, currentB);
  for (int i = 0; i < NUM_PIXELS; i++) {
    strip.setPixelColor(i, color);
  }
  strip.show();
}

void flashLed(int r, int g, int b, int flashes, int onMs, int offMs) {
  int baseR = constrain(r, 0, 255);
  int baseG = constrain(g, 0, 255);
  int baseB = constrain(b, 0, 255);
  int brightR = min(255, baseR + 70);
  int brightG = min(255, baseG + 70);
  int brightB = min(255, baseB + 70);

  for (int i = 0; i < max(flashes, 1); i++) {
    setLedColor(brightR, brightG, brightB);
    delay(max(onMs, 20));
    setLedColor(0, 0, 0);
    delay(max(offMs, 20));
  }

  setLedColor(baseR, baseG, baseB);
}

void writeServoPair(int leftAngle, int rightAngle) {
  leftServo.write(constrain(leftAngle, 15, 165));
  rightServo.write(constrain(rightAngle, 15, 165));
  currentLeftAngle = constrain(leftAngle, 15, 165);
  currentRightAngle = constrain(rightAngle, 15, 165);
}

void moveServosSmooth(int fromLeft, int toLeft, int fromRight, int toRight, int stepDelayMs) {
  int leftSteps = abs(toLeft - fromLeft);
  int rightSteps = abs(toRight - fromRight);
  int totalSteps = max(leftSteps, rightSteps);

  if (totalSteps == 0) {
    writeServoPair(toLeft, toRight);
    return;
  }

  for (int step = 0; step <= totalSteps; step++) {
    int leftAngle = fromLeft + ((toLeft - fromLeft) * step) / totalSteps;
    int rightAngle = fromRight + ((toRight - fromRight) * step) / totalSteps;
    leftServo.write(leftAngle);
    rightServo.write(rightAngle);
    delay(stepDelayMs);
  }
  writeServoPair(toLeft, toRight);
}

void nod(int cycles, int centerAngle, int amplitude, int stepDelayMs) {
  for (int i = 0; i < cycles; i++) {
    moveServosSmooth(currentLeftAngle, centerAngle - amplitude, currentRightAngle, centerAngle - amplitude, stepDelayMs);
    moveServosSmooth(currentLeftAngle, centerAngle + amplitude, currentRightAngle, centerAngle + amplitude, stepDelayMs);
    moveServosSmooth(currentLeftAngle, centerAngle, currentRightAngle, centerAngle, stepDelayMs);
  }
}

void wiggle(int cycles, int centerAngle, int amplitude, int stepDelayMs) {
  for (int i = 0; i < cycles; i++) {
    moveServosSmooth(currentLeftAngle, centerAngle + amplitude, currentRightAngle, centerAngle - amplitude, stepDelayMs);
    moveServosSmooth(currentLeftAngle, centerAngle - amplitude, currentRightAngle, centerAngle + amplitude, stepDelayMs);
  }
  moveServosSmooth(currentLeftAngle, centerAngle, currentRightAngle, centerAngle, stepDelayMs);
}

void handleCommand(String line) {
  line.trim();
  if (line.length() == 0) {
    return;
  }

  if (line.startsWith("LED")) {
    int r, g, b;
    int parsed = sscanf(line.c_str(), "LED %d %d %d", &r, &g, &b);
    if (parsed == 3) {
      setLedColor(r, g, b);
      Serial.println("OK LED");
      return;
    }
  }

  if (line.startsWith("FLASH")) {
    int r, g, b, flashes, onMs, offMs;
    int parsed = sscanf(line.c_str(), "FLASH %d %d %d %d %d %d", &r, &g, &b, &flashes, &onMs, &offMs);
    if (parsed == 6) {
      flashLed(r, g, b, flashes, onMs, offMs);
      Serial.println("OK FLASH");
      return;
    }
  }

  if (line.startsWith("SERVO")) {
    int angle, stepDelayMs;
    int parsed = sscanf(line.c_str(), "SERVO %d %d", &angle, &stepDelayMs);
    if (parsed == 2) {
      angle = constrain(angle, 15, 165);
      moveServosSmooth(currentLeftAngle, angle, currentRightAngle, angle, max(stepDelayMs, 5));
      Serial.println("OK SERVO");
      return;
    }
  }

  if (line.startsWith("NOD")) {
    int cycles, centerAngle, amplitude, stepDelayMs;
    int parsed = sscanf(line.c_str(), "NOD %d %d %d %d", &cycles, &centerAngle, &amplitude, &stepDelayMs);
    if (parsed == 4) {
      nod(max(cycles, 1), constrain(centerAngle, 15, 165), constrain(amplitude, 5, 45), max(stepDelayMs, 5));
      Serial.println("OK NOD");
      return;
    }
  }

  if (line.startsWith("WIGGLE")) {
    int cycles, centerAngle, amplitude, stepDelayMs;
    int parsed = sscanf(line.c_str(), "WIGGLE %d %d %d %d", &cycles, &centerAngle, &amplitude, &stepDelayMs);
    if (parsed == 4) {
      wiggle(max(cycles, 1), constrain(centerAngle, 15, 165), constrain(amplitude, 5, 45), max(stepDelayMs, 5));
      Serial.println("OK WIGGLE");
      return;
    }
  }

  if (line == "PING") {
    Serial.println("PONG");
    return;
  }

  if (line == "SLEEP") {
    moveServosSmooth(currentLeftAngle, 90, currentRightAngle, 90, 10);
    setLedColor(0, 0, 0);
    Serial.println("OK SLEEP");
    return;
  }

  Serial.print("ERR ");
  Serial.println(line);
}

void setup() {
  Serial.begin(115200);

  leftServo.attach(LEFT_SERVO_PIN);
  rightServo.attach(RIGHT_SERVO_PIN);
  writeServoPair(currentLeftAngle, currentRightAngle);

  strip.begin();
  strip.setBrightness(35);
  strip.show();

  setLedColor(0, 80, 0);
  Serial.println("PLANT_READY");
}

void loop() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n') {
      handleCommand(inputLine);
      inputLine = "";
    } else if (c != '\r') {
      inputLine += c;
    }
  }
}
