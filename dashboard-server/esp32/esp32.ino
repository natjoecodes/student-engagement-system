#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>

// --- SENSOR PINS ---
#define DHTPIN 4
#define DHTTYPE DHT22
#define MQ135_PIN 34
#define LDR_PIN 35
#define KY037_PIN 32

// --- WIFI & SERVER CONFIGURATION ---
const char* ssid = "Nat Joe";
const char* password = "Nathan@6451";
// IMPORTANT: Make sure this IP is correct for your computer running the Flask server
const String serverName = "http://172.20.10.2:5000/update-sensor";

DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(115200);
  dht.begin();

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected!");
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    float temperature = dht.readTemperature();
    float humidity = dht.readHumidity();

    // --- READ RAW ANALOG VALUES ---
    int rawAirQuality = analogRead(MQ135_PIN);
    // The LDR value is inverted; more light = lower analog value. So we subtract from the max.
    int rawLightLevel = 4095 - analogRead(LDR_PIN); 
    int rawSoundLevel = analogRead(KY037_PIN);

    // --- CONVERT RAW VALUES TO MEANINGFUL UNITS ---
    // Map the raw air quality reading to an approximate PPM scale.
    // 400 is fresh air, 5000 is a very high concentration.
    long co2_ppm = map(rawAirQuality, 0, 4095, 400, 5000);

    // Map the raw light level to a Lux-like scale (0-1000)
    long light_lux = map(rawLightLevel, 0, 4095, 0, 1000);

    // Map the raw sound level to an approximate decibel (dB) scale.
    // 30 is a quiet room, 100 is very loud.
    long sound_db = map(rawSoundLevel, 0, 4095, 30, 100);

    if (isnan(temperature) || isnan(humidity)) {
      Serial.println("Failed to read DHT sensor!");
      delay(2000);
      return;
    }

    HTTPClient http;
    http.begin(serverName);
    http.addHeader("Content-Type", "application/json");

    // Construct the JSON payload with the NEW, converted values
    String jsonData = "{\"temperature\":" + String(temperature, 2) +
                      ",\"humidity\":" + String(humidity, 2) +
                      ",\"light\":" + String(light_lux) +
                      ",\"noise\":" + String(sound_db) +
                      ",\"co2\":" + String(co2_ppm) + "}";

    // For debugging in Serial Monitor:
    Serial.println("Sending data: " + jsonData);

    int httpResponseCode = http.POST(jsonData);
    if (httpResponseCode > 0) {
      Serial.print("HTTP Response code: ");
      Serial.println(httpResponseCode);
    } else {
      Serial.print("Error code: ");
      Serial.println(httpResponseCode);
    }

    http.end();
  } else {
    Serial.println("WiFi Disconnected");
  }

  delay(5000);
}

