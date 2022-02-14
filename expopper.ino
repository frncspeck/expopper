#include <Wire.h>
#include <Adafruit_I2CDevice.h>
#include <Adafruit_I2CRegister.h>
#include "Adafruit_MCP9600.h"
#include <LiquidCrystal.h>

#define I2C_ADDRESS (0x67)

Adafruit_MCP9600 mcp;
float HotJunctionTemp = 0;

//Init
int startRoast = 0;

//LiquidCrystal lcd(12, 11, 5, 4, 3, 2);
const int rs = 12, en = 11, d4 = 5, d5 = 4, d6 = 3, d7 = 2;
LiquidCrystal lcd(rs, en, d4, d5, d6, d7);
unsigned long timer;

// Button logic
const int CrackButton  = 7;//A1;
const int LED       = 13;  // the Uno LED
int ButtonState     = 0;   // take current button state
int LastButtonState = 0;   // take last button state
int LEDState        = 0;   // take light status

// Relais logic
const int Relais1 = 8;
const int Relais2 = 9;
int relais_cycle = 0; // if set to higher value will cycle
int relais_counter = 0; // during cycling used as counter
int relais_state = 0; // during cycling used to toggle state 

// Serial controller
int incomingByte = 0;

void start2Roast()
{
    lcd.begin(16, 2);
    lcd.print("TC degrees C");
    startRoast = millis();
    digitalWrite(Relais1, LOW);
}

void in2Roast()
{
  lcd.setCursor(0, 1);
  //Print seconds since start -> timing
  timer = (millis() - startRoast) / 1000; // in seconds
  HotJunctionTemp = mcp.readThermocouple();
  lcd.print(timer); lcd.print(' '); lcd.print(HotJunctionTemp);

  if (relais_cycle > 0) {
    if (relais_counter > 0) {
      relais_counter -= 1;
    } else {
      relais_counter = relais_cycle;
      if (relais_state == 1) {
        relais_state = 0;
        digitalWrite(Relais1, HIGH);
      } else {
        relais_state = 1;
        digitalWrite(Relais1, LOW);
      }
    }
  }  
}

void stop2Roast()
{
    // LCD setup
    lcd.begin(16, 2);
    lcd.print("Waiting 2 start");
    relais_cycle = 0;
    digitalWrite(Relais1, HIGH);
    startRoast = 0;
}

void setup()
{
    // Button setup
    pinMode(CrackButton, INPUT_PULLUP);
    pinMode(LED, OUTPUT);

    // Relais setup
    pinMode(Relais1, OUTPUT);
    
    // Thermocouple setup
    Serial.begin(115200);
    while (!Serial) {
      delay(10);
    }
    Serial.println("MCP9600 HW test");

    /* Initialise the driver with I2C_ADDRESS and the default I2C bus. */
    if (! mcp.begin(I2C_ADDRESS)) {
        Serial.println("Sensor not found. Check wiring!");
        while (1);
    }

  Serial.println("Found MCP9600!");

  mcp.setADCresolution(MCP9600_ADCRESOLUTION_18);
  Serial.print("ADC resolution set to ");
  switch (mcp.getADCresolution()) {
    case MCP9600_ADCRESOLUTION_18:   Serial.print("18"); break;
    case MCP9600_ADCRESOLUTION_16:   Serial.print("16"); break;
    case MCP9600_ADCRESOLUTION_14:   Serial.print("14"); break;
    case MCP9600_ADCRESOLUTION_12:   Serial.print("12"); break;
  }
  Serial.println(" bits");

  mcp.setThermocoupleType(MCP9600_TYPE_K);
  Serial.print("Thermocouple type set to ");
  switch (mcp.getThermocoupleType()) {
    case MCP9600_TYPE_K:  Serial.print("K"); break;
    case MCP9600_TYPE_J:  Serial.print("J"); break;
    case MCP9600_TYPE_T:  Serial.print("T"); break;
    case MCP9600_TYPE_N:  Serial.print("N"); break;
    case MCP9600_TYPE_S:  Serial.print("S"); break;
    case MCP9600_TYPE_E:  Serial.print("E"); break;
    case MCP9600_TYPE_B:  Serial.print("B"); break;
    case MCP9600_TYPE_R:  Serial.print("R"); break;
  }
  Serial.println(" type");

  mcp.setFilterCoefficient(3);
  Serial.print("Filter coefficient value set to: ");
  Serial.println(mcp.getFilterCoefficient());

  mcp.setAlertTemperature(1, 30);
  Serial.print("Alert #1 temperature set to ");
  Serial.println(mcp.getAlertTemperature(1));
  mcp.configureAlert(1, true, true);  // alert 1 enabled, rising temp

  mcp.enable(true);

  Serial.println(F("------------------------------"));

  stop2Roast();

}

void loop()
{
  //Crack button logic
  ButtonState = digitalRead(CrackButton);
  if (LastButtonState == 0 && ButtonState == 1)
  {
    if (LEDState == 0)
    {
      digitalWrite(LED, HIGH);
      LEDState = 1;
    }
    else
    {
      digitalWrite(LED, LOW);
      LEDState = 0;
    }    
  }
  LastButtonState = ButtonState;

  if ( startRoast != 0 ) {
    in2Roast();
  }

  if (Serial.available() > 0) {
    incomingByte = Serial.read();
    
    if (incomingByte == 103) { // 103 == g == start roast
      start2Roast();
    }
    else if (incomingByte == 97) { // 97 == a == arrest roast
      stop2Roast();
    }
    else if (incomingByte == 114) { // 114 == r == activate relais
      // Cycle time is set to the multiple of the next 2 byte characters
      relais_cycle = Serial.read()*Serial.read();
    }
    else if (incomingByte == 115) {  // 115 == s == send data
      Serial.print("Time: "); Serial.println(timer);
      Serial.print("Hot Junction: "); Serial.println(HotJunctionTemp);
      Serial.print("Cold Junction: "); Serial.println(mcp.readAmbient());
      Serial.print("ADC: "); Serial.print(mcp.readADC() * 2); Serial.println(" uV");
      Serial.print("Crack: "); Serial.println(LEDState);
    }
    else {
      Serial.print("Received: ");
      Serial.println(incomingByte, DEC);
    }
  }

  delay(100);
}

