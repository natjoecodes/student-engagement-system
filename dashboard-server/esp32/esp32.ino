#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>

// --- SENSOR PINS ---
#define DHTPIN 4
#define DHTTYPE DHT22
#define MQ135_PIN 35
#define LDR_PIN 34
#define KY037_PIN 32

// --- WIFI & SERVER CONFIGURATION ---
const char* ssid = "Nat Joe";
const char* password = "spotnatjoe1";
const String serverName = "http://172.20.10.4:5000/update-sensor";

DHT dht(DHTPIN, DHTTYPE);

// Helper function to print WiFi status clearly
void printWiFiStatus() {
  wl_status_t status = WiFi.status();

  Serial.print("WiFi status: ");
  switch (status) {
    case WL_IDLE_STATUS:
      Serial.println("IDLE");
      break;
    case WL_NO_SSID_AVAIL:
      Serial.println("SSID NOT FOUND");
      break;
    case WL_SCAN_COMPLETED:
      Serial.println("SCAN COMPLETED");
      break;
    case WL_CONNECTED:
      Serial.println("CONNECTED");
      Serial.print("ESP32 IP address: ");
      Serial.println(WiFi.localIP());
      Serial.print("Signal strength (RSSI): ");
      Serial.println(WiFi.RSSI());
      break;
    case WL_CONNECT_FAILED:
      Serial.println("CONNECT FAILED");
      break;
    case WL_CONNECTION_LOST:
      Serial.println("CONNECTION LOST");
      break;
    case WL_DISCONNECTED:
      Serial.println("DISCONNECTED");
      break;
    default:
      Serial.println("UNKNOWN");
      break;
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  dht.begin();

  Serial.println("Starting WiFi connection...");
  Serial.print("Connecting to SSID: ");
  Serial.println(ssid);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  // Add status reporting here
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(1000);
    Serial.print("Attempt ");
    Serial.print(attempts + 1);
    Serial.print(" - ");
    printWiFiStatus();
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("WiFi connected successfully.");
    printWiFiStatus();
  } else {
    Serial.println("WiFi failed to connect.");
    printWiFiStatus();
  }
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    float temperature = dht.readTemperature();
    float humidity = dht.readHumidity();

    int rawAirQuality = analogRead(MQ135_PIN);
    int rawLightLevel = 4095 - analogRead(LDR_PIN);
    int rawSoundLevel = analogRead(KY037_PIN);

    long co2_ppm = map(rawAirQuality, 0, 4095, 400, 5000);
    long light_lux = map(rawLightLevel, 0, 4095, 0, 1000);
    long sound_db = map(rawSoundLevel, 0, 4095, 30, 100);

    if (isnan(temperature) || isnan(humidity)) {
      Serial.println("Failed to read DHT sensor!");
      delay(2000);
      return;
    }

    HTTPClient http;
    http.begin(serverName);
    http.addHeader("Content-Type", "application/json");

    String jsonData = "{\"temperature\":" + String(temperature, 2) +
                      ",\"humidity\":" + String(humidity, 2) +
                      ",\"light\":" + String(light_lux) +
                      ",\"noise\":" + String(sound_db) +
                      ",\"co2\":" + String(co2_ppm) + "}";

    Serial.println("Sending data: " + jsonData);

    int httpResponseCode = http.POST(jsonData);
    if (httpResponseCode > 0) {
      Serial.print("HTTP Response code: ");
      Serial.println(httpResponseCode);
    } else {
      Serial.print("HTTP Error code: ");
      Serial.println(httpResponseCode);
    }

    http.end();
  } else {
    Serial.println("WiFi disconnected in loop.");
    printWiFiStatus();

    Serial.println("Trying to reconnect...");
    WiFi.disconnect();
    WiFi.begin(ssid, password);
  }

  delay(5000);
}