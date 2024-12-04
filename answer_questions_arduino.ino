#include <Servo.h>

// Define the number of users
const int userCount = 4;  // Changed from 3 to 4

// Define pin arrays
const int buttonPins[] = {2, 3, 4, 5};   // Button pins for users 0 to 3
const int ledPins[] = {6, 7, 8, 9};      // LED pins for users 0 to 3
const int servoPins[] = {10, 11, 12, 13}; // Servo motor pins for users 0 to 3


Servo mouthServos[userCount];  // Array of servo objects

int buttonStates[userCount];     // Array of button states
int servoAngles[userCount];      // Array of servo angles

bool isLocked = false;           // Indicates whether the system is locked
int currentResponder = -1;       // Index of the current responder

void setup() {
  Serial.begin(9600);
  for (int i = 0; i < userCount; i++) {
    pinMode(buttonPins[i], INPUT_PULLUP);
    pinMode(ledPins[i], OUTPUT);
    mouthServos[i].attach(servoPins[i]);
    servoAngles[i] = 0;
    mouthServos[i].write(servoAngles[i]);
  }
}

void loop() {
  // Check buttons and servo states
  if (!isLocked) {
    for (int i = 0; i < userCount; i++) {
      // Check if the servo has already rotated to 180 degrees
      if (servoAngles[i] >= 180) {
        // User loses the right to answer, skip
        continue;
      }

      // Read button state
      buttonStates[i] = digitalRead(buttonPins[i]);
      if (buttonStates[i] == LOW) {
        // Button is pressed, send buzzer signal
        Serial.print("BUZZER:");
        Serial.println(i);
        currentResponder = i;  // Record the current responder
        isLocked = true;       // Lock the buzzer
        // Prevent repeated sending
        delay(500);
        break;  // Exit the loop to prevent multiple users from buzzing simultaneously
      }
    }
  }

  // Check for commands from Python
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    // Parse the command
    if (command.startsWith("LED_ON:")) {
      int index = command.substring(7).toInt();
      if (index >= 0 && index < userCount) {
        digitalWrite(ledPins[index], HIGH);
      }
    } else if (command.startsWith("LED_OFF:")) {
      int index = command.substring(8).toInt();
      if (index >= 0 && index < userCount) {
        digitalWrite(ledPins[index], LOW);
      }
    } else if (command.startsWith("ROTATE:")) {
      int index = command.substring(7).toInt();
      if (index >= 0 && index < userCount) {
        servoAngles[index] += 60;
        if (servoAngles[index] > 180) servoAngles[index] = 180;
        mouthServos[index].write(servoAngles[index]);
      }
    } else if (command.startsWith("UNLOCK")) {
      isLocked = false;       // Unlock the buzzer
      currentResponder = -1;  // Reset the current responder
    }
  }
}
