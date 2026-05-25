#include <WiFi.h>
#include <WebServer.h>

const int in1 = 26, in2 = 25, in3 = 33, in4 = 32;

const char* ssid = "Network_SSID";
const char* password = "password";

WebServer server(80);

// Speed levels
const int SPEED_LOW    = 100;  // ~39%
const int SPEED_MEDIUM = 180;  // ~70%
const int SPEED_HIGH   = 255;  // 100%

int currentSpeed = SPEED_MEDIUM;  // Default: medium

void sendResponse(String message) {
  server.send(200, "text/plain", message);
}

void setMotors(int left1, int left2, int right1, int right2) {
  analogWrite(in1, left1);
  analogWrite(in2, left2);
  analogWrite(in3, right1);
  analogWrite(in4, right2);
}

void setup() {
  Serial.begin(115200);
  pinMode(in1, OUTPUT); pinMode(in2, OUTPUT);
  pinMode(in3, OUTPUT); pinMode(in4, OUTPUT);

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());

  // Direction routes
  server.on("/F", forward);
  server.on("/B", backward);
  server.on("/L", left);
  server.on("/R", right);
  server.on("/S", stopCar);

  // Speed routes
  server.on("/SPD/LOW",    speedLow);
  server.on("/SPD/MED",    speedMedium);
  server.on("/SPD/HIGH",   speedHigh);

  server.begin();
}

void loop() {
  server.handleClient();
}

// --- Speed Handlers ---
void speedLow()    { currentSpeed = SPEED_LOW;    sendResponse("Speed: Low");    Serial.println("Speed set to LOW");    }
void speedMedium() { currentSpeed = SPEED_MEDIUM;  sendResponse("Speed: Medium");  Serial.println("Speed set to MEDIUM");  }
void speedHigh()   { currentSpeed = SPEED_HIGH;    sendResponse("Speed: High");    Serial.println("Speed set to HIGH");    }

// --- Direction Handlers ---
void forward()  { setMotors(0, currentSpeed, 0, currentSpeed); sendResponse("Forward");  }
void backward() { setMotors(currentSpeed, 0, currentSpeed, 0); sendResponse("Backward"); }
void right()    { setMotors(0, currentSpeed, currentSpeed, 0); sendResponse("Right");    }
void left()     { setMotors(currentSpeed, 0, 0, currentSpeed); sendResponse("Right");    }
void stopCar()  { setMotors(0, 0, 0, 0);                       sendResponse("Stop");     }