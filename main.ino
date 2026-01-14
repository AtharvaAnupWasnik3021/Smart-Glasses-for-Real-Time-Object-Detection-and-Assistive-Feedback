#include <WiFi.h>

const int touchPin = 16;
const int irPin = 4;
const int trigPin = 13;
const int echoPin = 12;
const int buzzPin = 25;

const char* ssid = "Atharva's F16";
const char* password = "atharva123";

WiFiServer server(80);

void setup() {
  Serial.begin(115200);
  
  pinMode(touchPin, INPUT);
  pinMode(irPin, INPUT);
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  pinMode(buzzPin, INPUT);

  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected!");
  Serial.print("ESP32 IP Address: ");
  Serial.println(WiFi.localIP());

  server.begin();
}

void loop() {
  WiFiClient client = server.available();
  if (!client) return;

  while (!client.available()) {
    delay(1);
  }

  String request = client.readStringUntil('\r');
  client.flush();

  int touchState = digitalRead(touchPin);
  int irValue = 0;
  long distance = 0;

  if (touchState == HIGH) {
    irValue = digitalRead(irPin);

    digitalWrite(trigPin, LOW);
    delayMicroseconds(2);
    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);

    long duration = pulseIn(echoPin, HIGH);
    distance = (duration * 0.034) / 2;
    if(distance < 100){
      digitalWrite(buzzPin, HIGH);
      Serial.println("Buzzz");
    }
  }

  String html = "<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'>";
  html += "<style>body{font-family:Arial;text-align:center;background:#121212;color:#fff;}h1{color:#00e676;}div{margin:20px;padding:20px;border-radius:10px;background:#1f1f1f;}</style>";
  html += "</head><body><h1>ESP32 Sensor Monitor</h1>";
  html += "<div><h3>Touch Sensor: " + String(touchState == HIGH ? "Pressed" : "Not Pressed") + "</h3>";

  if (touchState == HIGH) {
    html += "<h3>IR Sensor: " + String(!irValue ? "Object Detected" : "No Object") + "</h3>";
    html += "<h3>Ultrasonic Distance: " + String(distance) + " cm</h3>";
    html += "<h3>Buzzer Active: " + String(distance < 100 ? "True" : "False") + " </h3>";
  } else {
    html += "<h3>Sensors inactive (Touch not pressed)</h3>";
  }

  html += "<p><a href='/'><button style='padding:10px 20px;border:none;border-radius:8px;background:#00e676;color:#000;font-size:16px;'>Refresh</button></a></p>";
  html += "</div></body></html>";

  client.println("HTTP/1.1 200 OK");
  client.println("Content-type:text/html");
  client.println();
  client.println(html);
  client.stop();
}
