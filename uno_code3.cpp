// Arduino Uno R3 — Traffic Lights with Ambulance Priority + Blinking

// Quadrant LED pins
const int greenPins[4] = {2, 4, 6, 8};
const int redPins[4]   = {3, 5, 7, 9};

// Data arrays
int carCounts[4] = {5, 5, 5, 5};       // default = 5 sec each
int ambCounts[4] = {0, 0, 0, 0};       // default = no ambulances

int currentQuadrant = 0;

void setup() {
  Serial.begin(9600);
  for (int i = 0; i < 4; i++) {
    pinMode(greenPins[i], OUTPUT);
    pinMode(redPins[i], OUTPUT);
  }
  Serial.println("System ready. Waiting for data...");
}

void loop() {
  // --- Handle incoming serial data ---
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    parseInput(input);
    Serial.println("ACK");  // acknowledge receipt
  }

  // --- Traffic light cycle ---
  handleQuadrant(currentQuadrant);

  // Move to next quadrant
  currentQuadrant = (currentQuadrant + 1) % 4;
}

// Function to handle traffic lights for one quadrant
void handleQuadrant(int q) {
  // Turn this quadrant green (or blinking), others red
  for (int i = 0; i < 4; i++) {
    if (i == q) {
      digitalWrite(redPins[i], LOW);  // active quadrant red OFF
    } else {
      digitalWrite(greenPins[i], LOW);
      digitalWrite(redPins[i], HIGH); // non-active quadrants red ON
    }
  }

  // --- Ambulance priority ---
  if (ambCounts[q] > 0) {
    Serial.print("Quadrant ");
    Serial.print(q);
    Serial.println(" ambulance priority active.");

    // Stay green-blinking until ambulance count = 0
    while (ambCounts[q] > 0) {
      // Blink green ON
      digitalWrite(greenPins[q], HIGH);
      delay(300);

      // Blink green OFF
      digitalWrite(greenPins[q], LOW);
      delay(200);

      // Listen for new data while blinking
      if (Serial.available()) {
        String input = Serial.readStringUntil('\n');
        input.trim();
        parseInput(input);
        Serial.println("ACK");
      }
    }

    // Once ambulance cleared, wait for car-based green time (steady ON)
    int waitTime = (carCounts[q] > 0 ? carCounts[q]*2 : 0.5) * 1000;
    digitalWrite(greenPins[q], HIGH);
    delay(waitTime);
  } else {
    // Normal car-based green time (steady ON)
    int waitTime = (carCounts[q] > 0 ? carCounts[q]*2 : 0.5) * 1000;
    digitalWrite(greenPins[q], HIGH);
    delay(waitTime);
  }
}

// Parse incoming CSV input into carCounts[] and ambCounts[]
void parseInput(String input) {
  int values[8];
  int idx = 0;
  while (input.length() > 0 && idx < 8) {
    int commaIndex = input.indexOf(',');
    String token;
    if (commaIndex == -1) {
      token = input;
      input = "";
    } else {
      token = input.substring(0, commaIndex);
      input = input.substring(commaIndex + 1);
    }
    values[idx] = token.toInt();
    idx++;
  }

  // Update arrays
  for (int i = 0; i < 4; i++) carCounts[i] = values[i];
  for (int i = 0; i < 4; i++) ambCounts[i] = values[i + 4];

  Serial.print("Updated counts. Cars: ");
  for (int i = 0; i < 4; i++) { Serial.print(carCounts[i]); Serial.print(" "); }
  Serial.print(" | Ambulances: ");
  for (int i = 0; i < 4; i++) { Serial.print(ambCounts[i]); Serial.print(" "); }
  Serial.println();
}
