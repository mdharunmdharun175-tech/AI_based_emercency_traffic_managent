/*
 * AI Traffic System - Arduino Signal Controller
 * Receives serial commands from Raspberry Pi / PC and controls traffic signals.
 *
 * Wiring:
 *   L1 RED   → Pin 2   L1 GREEN → Pin 3
 *   L2 RED   → Pin 4   L2 GREEN → Pin 5
 *   L3 RED   → Pin 6   L3 GREEN → Pin 7
 *   L4 RED   → Pin 8   L4 GREEN → Pin 9
 *   Buzzer   → Pin 10  (optional: siren alert)
 *
 * Serial Protocol:
 *   Command: "L1:G;L2:R;L3:R;L4:R;"
 *   G = GREEN, R = RED, Y = YELLOW
 *   Each command ends with newline '\n'
 */

// Pin definitions
const int LANE_PINS[4][2] = {
  {2, 3},   // L1: {RED, GREEN}
  {4, 5},   // L2: {RED, GREEN}
  {6, 7},   // L3: {RED, GREEN}
  {8, 9},   // L4: {RED, GREEN}
};
const int BUZZER_PIN = 10;
const int LED_STATUS = 13;  // onboard LED = system active

// Current state
char laneStates[4] = {'R', 'R', 'R', 'R'};
bool emergencyMode = false;
unsigned long lastCmd = 0;
const unsigned long TIMEOUT_MS = 10000;  // revert to safe state after 10s no command

void setup() {
  Serial.begin(9600);
  for (int i = 0; i < 4; i++) {
    pinMode(LANE_PINS[i][0], OUTPUT);  // RED
    pinMode(LANE_PINS[i][1], OUTPUT);  // GREEN
  }
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_STATUS, OUTPUT);

  allRed();  // safe default
  digitalWrite(LED_STATUS, HIGH);
  Serial.println("READY");
}

void loop() {
  // Read serial command
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.length() > 0) {
      processCommand(cmd);
      lastCmd = millis();
    }
  }

  // Watchdog: if no command received for TIMEOUT_MS, go to safe state
  if (millis() - lastCmd > TIMEOUT_MS && lastCmd != 0) {
    allRed();
    emergencyMode = false;
  }

  // Blink status LED
  digitalWrite(LED_STATUS, (millis() / 500) % 2);
}

/*
 * Parse command string: "L1:G;L2:R;L3:G;L4:R;"
 * Update relay/LED outputs accordingly.
 */
void processCommand(String cmd) {
  bool hasGreen = false;
  int greenLane = -1;

  // Parse each segment e.g. "L1:G"
  int start = 0;
  while (start < (int)cmd.length()) {
    int sep = cmd.indexOf(';', start);
    if (sep == -1) break;
    String seg = cmd.substring(start, sep);
    seg.trim();
    start = sep + 1;

    if (seg.length() < 4) continue;  // "L1:G" = 4 chars minimum

    int laneIdx = seg[1] - '1';  // '1'→0, '2'→1, '3'→2, '4'→3
    if (laneIdx < 0 || laneIdx > 3) continue;

    char state = seg[3];  // G, R, or Y
    laneStates[laneIdx] = state;

    if (state == 'G') {
      hasGreen = true;
      greenLane = laneIdx;
    }
  }

  // Apply outputs
  for (int i = 0; i < 4; i++) {
    applyLane(i, laneStates[i]);
  }

  // Emergency mode: buzz if green corridor just opened
  if (hasGreen && greenLane >= 0) {
    if (!emergencyMode) {
      emergencyMode = true;
      alertBuzzer();
    }
  } else {
    emergencyMode = false;
    noTone(BUZZER_PIN);
  }

  Serial.print("OK:");
  Serial.println(cmd);
}

void applyLane(int lane, char state) {
  int redPin   = LANE_PINS[lane][0];
  int greenPin = LANE_PINS[lane][1];

  switch (state) {
    case 'G':
      digitalWrite(redPin,   LOW);
      digitalWrite(greenPin, HIGH);
      break;
    case 'Y':
      // For yellow: blink both (simplified — use timer interrupt for production)
      digitalWrite(redPin,   HIGH);
      digitalWrite(greenPin, LOW);
      break;
    case 'R':
    default:
      digitalWrite(redPin,   HIGH);
      digitalWrite(greenPin, LOW);
      break;
  }
}

void allRed() {
  for (int i = 0; i < 4; i++) {
    digitalWrite(LANE_PINS[i][0], HIGH);  // RED on
    digitalWrite(LANE_PINS[i][1], LOW);   // GREEN off
    laneStates[i] = 'R';
  }
}

void alertBuzzer() {
  // Two short beeps = emergency corridor open
  for (int i = 0; i < 2; i++) {
    tone(BUZZER_PIN, 1000, 150);
    delay(200);
  }
}
