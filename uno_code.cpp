/* QuadTrafficController_MinimalSerial.ino
   Same logic as before (4 quadrants with green/red LEDs).
   Serial is SILENT except when a valid new 4-number set is received:
     -> respond with "OK\n"
   No heartbeats or debug prints.

   Green pins: A=2, B=4, C=6, D=8
   Red   pins: A=3, B=5, C=7, D=9
*/

const uint8_t GREEN_PINS[4] = { 2, 4, 6, 8 }; // A, B, C, D
const uint8_t RED_PINS[4]   = { 3, 5, 7, 9 }; // A, B, C, D

// default times (seconds)
unsigned long timesSec[4] = {5, 5, 5, 5}; // A,B,C,D

// runtime variables
uint8_t activeIndex = 0; // 0=A,1=B,2=C,3=D
unsigned long activeStartMillis = 0;
unsigned long activeDurationMs = 5000; // current active duration in ms (derived from timesSec[activeIndex])

// Serial input buffer
String serialBuf = "";

// limits
const unsigned long MAX_SECONDS = 3600UL; // 1 hour max per quadrant

void setup() {
  // init pins
  for (uint8_t i=0;i<4;i++) {
    pinMode(GREEN_PINS[i], OUTPUT);
    pinMode(RED_PINS[i], OUTPUT);
  }

  // Initialize lights (active A)
  applyLightsForActive(activeIndex);

  activeDurationMs = timesSec[activeIndex] * 1000UL;
  activeStartMillis = millis();

  // Serial for control (only used to receive commands and send OK)
  Serial.begin(9600);
  // no startup prints to keep serial quiet
}

// Turn ON the green led of active quadrant and OFF its red,
// and for others turn OFF green and ON red.
void applyLightsForActive(uint8_t idx) {
  for (uint8_t i=0;i<4;i++) {
    if (i == idx) {
      digitalWrite(GREEN_PINS[i], HIGH);
      digitalWrite(RED_PINS[i], LOW);
    } else {
      digitalWrite(GREEN_PINS[i], LOW);
      digitalWrite(RED_PINS[i], HIGH);
    }
  }
}

// parse a string and set timesSec if valid; return true on success
bool parseAndSetTimes(String s) {
  s.trim();
  if (s.length() == 0) return false;

  if (s.startsWith("t:") || s.startsWith("T:")) {
    s = s.substring(2);
    s.trim();
  }

  // normalize separators to comma
  for (int i = 0; i < s.length(); ++i) {
    char c = s.charAt(i);
    if (c == ';' || c == ' ' || c == '\t') s.setCharAt(i, ',');
  }

  unsigned long newTimes[4];
  uint8_t found = 0;
  int start = 0;
  int len = s.length();

  while (start < len && found < 4) {
    int commaIdx = s.indexOf(',', start);
    String token;
    if (commaIdx == -1) {
      token = s.substring(start);
      start = len;
    } else {
      token = s.substring(start, commaIdx);
      start = commaIdx + 1;
    }
    token.trim();
    if (token.length() == 0) continue;

    bool negative = false;
    int pos = 0;
    if (token.charAt(0) == '-') { negative = true; pos = 1; }
    unsigned long val = 0;
    bool anyDigit = false;
    for (; pos < token.length(); ++pos) {
      char ch = token.charAt(pos);
      if (ch >= '0' && ch <= '9') {
        anyDigit = true;
        val = val * 10UL + (unsigned long)(ch - '0');
      } else {
        anyDigit = false;
        break;
      }
    }
    if (!anyDigit || negative) {
      return false; // invalid token -> reject entire input silently
    }
    if (val > MAX_SECONDS) val = MAX_SECONDS;
    newTimes[found++] = val;
  }

  if (found == 4) {
    for (uint8_t i=0;i<4;i++) timesSec[i] = newTimes[i];
    // update current duration so change is immediate
    activeDurationMs = timesSec[activeIndex] * 1000UL;
    if (activeDurationMs == 0) activeDurationMs = 500;
    activeStartMillis = millis();
    return true;
  }
  return false;
}

void loop() {
  // handle incoming serial characters (non-blocking)
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (serialBuf.length() > 0) {
        bool ok = parseAndSetTimes(serialBuf);
        if (ok) {
          // send single-line ACK (OK) and newline
          Serial.println("OK");
        }
        serialBuf = "";
      }
    } else {
      if (c >= 32) serialBuf += c;
      if (serialBuf.length() > 200) {
        serialBuf = ""; // defensive: drop if too long
      }
    }
  }

  // handle timing and quadrant switching (non-blocking)
  unsigned long now = millis();
  if (activeDurationMs == 0) activeDurationMs = 500;
  if ((now - activeStartMillis) >= activeDurationMs) {
    activeIndex = (activeIndex + 1) % 4;
    applyLightsForActive(activeIndex);
    activeDurationMs = timesSec[activeIndex] * 1000UL;
    if (activeDurationMs == 0) activeDurationMs = 500;
    activeStartMillis = now;
  }

  // tiny delay to avoid busy-looping; does not affect timing since we use millis()
  delay(5);
}
