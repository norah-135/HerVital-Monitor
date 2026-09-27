#include <Wire.h>

#define ST25DV_ADDR 0x53

const int ntcPin = A0;
const float SERIES_RESISTOR = 100000.0;     
const float NOMINAL_RESISTANCE = 100000.0; 
const float NOMINAL_TEMPERATURE = 25.0;
const float B_COEFFICIENT = 3950.0;        

void setup() {
  Serial.begin(115200);
  while (!Serial);

  Wire.begin();
  Wire.setClock(100000);

  Serial.println("تم بدء النظام والتواصل عبر I2C جاهز...");
}

void loop() {
  int adcValue = analogRead(ntcPin);
  if (adcValue <= 0) adcValue = 1;

  float resistance = SERIES_RESISTOR * ((1023.0 / (float)adcValue) - 1.0);

  float steinhart;
  steinhart = resistance / NOMINAL_RESISTANCE;
  steinhart = log(steinhart);
  steinhart /= B_COEFFICIENT;
  steinhart += 1.0 / (NOMINAL_TEMPERATURE + 273.15);
  steinhart = 1.0 / steinhart;
  float temperatureC = steinhart - 273.15;

  Serial.print("الحرارة: ");
  Serial.print(temperatureC, 1);
  Serial.println(" C");

  String msg = "Temp: " + String(temperatureC, 1) + " C";
  writeNDEF(msg);

  delay(3000);
}

void writeNDEF(String text) {
  uint8_t textLen = text.length();
  uint8_t payloadLen = textLen + 3;
  uint8_t recordLen = payloadLen + 4;

  uint8_t buffer[36];
  memset(buffer, 0, sizeof(buffer));

  buffer[0] = 0x03;               // NDEF TLV
  buffer[1] = recordLen;          
  buffer[2] = 0xD1;               
  buffer[3] = 0x01;               
  buffer[4] = payloadLen;         
  buffer[5] = 'T';                
  buffer[6] = 0x02;               
  buffer[7] = 'e';                
  buffer[8] = 'n';                

  for (uint8_t i = 0; i < textLen; i++) {
    buffer[9 + i] = text[i];
  }
  buffer[9 + textLen] = 0xFE;

  uint8_t totalBytes = 10 + textLen;

  // كتابة البيانات إلى EEPROM كل 4 بايت
  for (uint16_t offset = 0; offset < totalBytes; offset += 4) {
    uint16_t memAddr = 0x0004 + offset; // البداية من Block 1
    
    Wire.beginTransmission(ST25DV_ADDR);
    Wire.write((uint8_t)(memAddr >> 8));   
    Wire.write((uint8_t)(memAddr & 0xFF)); 
    
    for (uint8_t b = 0; b < 4; b++) {
      if (offset + b < totalBytes) {
        Wire.write(buffer[offset + b]);
      } else {
        Wire.write(0x00);
      }
    }
    byte status = Wire.endTransmission();
    if (status != 0) {
      Serial.print("خطأ I2C عند الإزاحة: ");
      Serial.println(offset);
      return;
    }
    delay(15); // وقت برمجة الذاكرة
  }

  Serial.println("-> تم تحديث الذاكرة بنجاح!");
}