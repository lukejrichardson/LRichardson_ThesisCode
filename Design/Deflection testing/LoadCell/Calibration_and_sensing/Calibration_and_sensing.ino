/*
Code to interface the UCT UAV thrust stand measurement rig sensors, microcontroller, and GUI.
By: Michael Thomson
Date: 2024/06/24

This code intends to combine the sensing and calibration functions based on information received from the GUI over serial.
*/

//Libraries//
#include "HX711.h" //Used for interfacing with load cells
#include <Servo.h> //Used for ESC control via PWM
#include <EEPROM.h> //Used to store calibration values
#include <Arduino.h> //Used for IR RPM sensor
#include <CRC16.h>

//Pin Definitions//
//Sensor Pins
#define THR_DOUT 3
#define THR_CLK  2
#define TRQ_DOUT  5
#define TRQ_CLK  4
#define RPM_PIN  7
//ESC Pin
#define ESC_PIN  6

//Calibration data EEPROM address
#define EEPROM_ADDRESS  0

//EEPROM Calibration Value Struct to store tare offset and gain for torque and thrust loadcells
//This should reduce the need to recalibrate on each power cycle
struct Settings {
  uint16_t sensor_poll_frequency;
  uint8_t pulses_per_rev;
  long thr_scale;
  long trq_scale;
};

Settings settings = {100, 1, 8500, 8500}; // Default values

//Global Variables//
HX711 thrust;
//HX711 torque;
Servo esc;

uint8_t throttle = 0;
uint8_t throttleOld = 0;
unsigned long const baudrate = 115200;
long stabilisingTime = 2000;
uint16_t sensor_poll_frequency = 100;
uint32_t last_sensor_poll = 0;

//Serial communication variables
const char endMarker = '\n';
int command = 0;
CRC16 crc(0x1021, 0xFFFF, 0x0000, false, false);

//Calibration variables
const uint32_t CALIBRATION_TIMEOUT = 40000; // 40 seconds in milliseconds
const uint8_t CALIBRATION_THRUST = 0;
const uint8_t CALIBRATION_TORQUE = 1;
unsigned long calibrationStartTime = 0;
uint8_t calibrationType = 0;
float calibrationValue = 0;
HX711* currentSensor;
long* currentScalePtr;

//IR RPM sensor variables//
//Store the number of sensor activations
volatile unsigned int revCounter = 0; 
//Last time the sensor was activated
unsigned long lastTime = 0;
//RPM value
unsigned int RPM = 0;
const unsigned long debounceTime = 1000;

//Setup Function to configure the board//
void setup() {
  //Create the serial connection and define input buttons.
  Serial.begin(baudrate);
  
  Serial.println("Setup beginning");
  // Load settings from EEPROM
  EEPROM.get(EEPROM_ADDRESS, settings);
  Serial.println("EEPROM Loaded");
  // Setup sensors
  thrust.begin(THR_DOUT, THR_CLK);
  Serial.println("Sensor started");
  thrust.set_scale(settings.thr_scale);
  Serial.println("Settings loaded");
  thrust.tare();
  Serial.println("Tare done");

  // torque.begin(TRQ_DOUT, TRQ_CLK);
  // torque.set_scale(settings.trq_scale);
  // torque.tare(20);
  
  //Setup RPM Sensor
  // pinMode(RPM_PIN, INPUT);
  // attachInterrupt(digitalPinToInterrupt(RPM_PIN), count_rotation, FALLING);
  // //Setup esc
  // init_esc();
  // pinMode(ESC_PIN, OUTPUT);
 

  //Wait until both load cells are ready to read
  while(!(thrust.is_ready()));
  
  Serial.println("Exiting setup()");
}

void loop() {
    uint32_t current_time = micros();

    // Handle incoming messages
    process_incoming_messages();

    // Calculate RPM
    if (millis() - lastTime >= debounceTime) {
        noInterrupts();
        RPM = (revCounter * 60UL * 1000UL) / (settings.pulses_per_rev * debounceTime);
        revCounter = 0;
        lastTime = millis();
        interrupts();
    }

    // Send sensor data if it's time
    if (current_time - last_sensor_poll >= 1000000UL / settings.sensor_poll_frequency) {
        last_sensor_poll = current_time;
        read_and_send_data();
    }
}

void init_esc(){
  //Initialises the ESC and sets the throttle range to calibrate
  esc.attach(ESC_PIN);
  esc.write(0);
  delay(stabilisingTime);
  esc.write(180);
  delay(stabilisingTime);
  esc.write(0);
  delay(stabilisingTime);
  throttle = 0;
  throttleOld = 0;
  

}

void count_rotation(){
  revCounter++;
}

void process_incoming_messages() {
  uint8_t message_type;
  uint8_t payload[32]; // Adjust size as needed
  uint32_t payload_length;

  if (receive_binary_message(message_type, payload, payload_length, 0)) { // 0 timeout for non-blocking
    switch (message_type) {
      // case 0x02: // Calibration command
      //   if (calibrationState == CAL_IDLE && payload_length == 5) {
      //     calibrationType = payload[0];
      //     memcpy(&calibrationValue, payload + 1, 4);
      //     start_calibration();
      //   } else if (calibrationState == CAL_GAIN_WAITING && payload_length == 1) {
      //     if (payload[0] == 1) {
      //       perform_gain_calibration();
      //     } else {
      //       cancel_calibration();
      //     }
      //   }
      //   break;
      case 0x04: // Set frequency command
        if (payload_length == 4) {
          uint32_t new_frequency;
          memcpy(&new_frequency, payload, 4);
          if (new_frequency > 0 && new_frequency <= 1000) {
            settings.sensor_poll_frequency = new_frequency;
            EEPROM.put(EEPROM_ADDRESS, settings);
            send_binary_message(0x03, (const uint8_t*)"Frequency updated", 17);
          } else {
            send_binary_message(0x03, (const uint8_t*)"Invalid frequency", 17);
          }
        }
        break;
      case 0x05: // Set throttle command
          if (payload_length == 1) {
              uint8_t new_throttle = payload[0];
              if (new_throttle <= 100) {
                  throttle = map(new_throttle, 0, 100, 0, 180);  // Map 0-100% to 0-180 for servo
                  analogWrite(ESC_PIN, throttle);
                  char message[32];
                  snprintf(message, sizeof(message), "Throttle set to %d%%", new_throttle);
                  send_status_message(message);
              } else {
                  send_status_message("Invalid throttle value");
              }
          }
          break;
      case 0x06: // Set pulses per revolution
        if (payload_length == 1) {
          uint8_t new_pulses = payload[0];
          if (new_pulses > 0 && new_pulses <= 10) { // Assuming max 10 blades
            settings.pulses_per_rev = new_pulses;
            EEPROM.put(EEPROM_ADDRESS, settings);
            send_binary_message(0x03, (const uint8_t*)"Pulses per rev updated", 22);
          } else {
            send_binary_message(0x03, (const uint8_t*)"Invalid pulses per rev", 22);
          }
        }
        break;
      case 0x07: // Combined settings command
        if (payload_length == 3) { // 2 bytes for polling rate, 1 byte for pulses per rev
          uint16_t new_poll_frequency;
          uint8_t new_pulses_per_rev;
          memcpy(&new_poll_frequency, payload, 2);
          new_pulses_per_rev = payload[2];
          
          if (new_poll_frequency >= 1 && new_poll_frequency <= 1000 &&
              new_pulses_per_rev >= 1 && new_pulses_per_rev <= 10) {
            settings.sensor_poll_frequency = new_poll_frequency;
            settings.pulses_per_rev = new_pulses_per_rev;
            EEPROM.put(0, settings);
            send_status_message("Settings updated successfully");
          } else {
            send_status_message("Invalid settings received");
          }
        }
        break;
    case 0x08: // Tare command
        if (payload_length == 1) {
            perform_tare(payload[0]);
        }
        break;
    case 0x09: // Gain calibration command
        if (payload_length == 5) {
            uint8_t sensor_type = payload[0];
            float calibration_value;
            memcpy(&calibration_value, payload + 1, 4);
            perform_gain_calibration(sensor_type, calibration_value);
        }
        break;
      default:
        send_binary_message(0x03, (const uint8_t*)"Unknown command", 15);
        break;
    }
  }
}

void perform_tare(uint8_t sensor_type) {
    HX711* sensor = (sensor_type == 0) ? &thrust : &thrust;
    const char* sensor_name = (sensor_type == 0) ? "Thrust" : "Thrust";
    
    send_status_message("Starting tare. Remove any load and wait.");
    sensor->tare(40);
    char message[64];
    snprintf(message, sizeof(message), "%s sensor tare completed.", sensor_name);
    send_status_message(message);
}

void perform_gain_calibration(uint8_t sensor_type, float calibration_value) {
    HX711* sensor = (sensor_type == 0) ? &thrust : &thrust;
    long* scale_ptr = (sensor_type == 0) ? &settings.thr_scale : &settings.thr_scale;
    const char* sensor_name = (sensor_type == 0) ? "Thrust" : "Thrust";

    send_status_message("Apply calibration load and wait.");
    delay(5000);  // Give user time to apply load
    
    double measured_value = sensor->get_value(10);
    *scale_ptr = measured_value / calibration_value;
    sensor->set_scale(*scale_ptr);
    
    // Save settings to EEPROM
    EEPROM.put(EEPROM_ADDRESS, settings);

    char message[64];
    snprintf(message, sizeof(message), "%s calibration completed. Scale: %ld", sensor_name, *scale_ptr);
    send_status_message(message);
}

void start_calibration() {
  if (calibrationType == CALIBRATION_THRUST) {
    currentSensor = &thrust;
    currentScalePtr = &settings.thr_scale;
  } else if (calibrationType == CALIBRATION_THRUST) {
    currentSensor = &thrust;
    currentScalePtr = &settings.thr_scale;
  } else {
    send_status_message("Invalid calibration type");
    return;
  }

  send_status_message("Starting tare. Remove any load and wait.");
  currentSensor->tare(10);
  send_status_message("Tare completed. Apply calibration load and send confirmation.");
}

void perform_gain_calibration() {
  
  double measured_value = currentSensor->get_value(10);
  *currentScalePtr = measured_value / calibrationValue;
  currentSensor->set_scale(*currentScalePtr);
  
  // Save settings to EEPROM
  EEPROM.put(EEPROM_ADDRESS, settings);

  char message[64];
  snprintf(message, sizeof(message), "Calibration completed. Scale: %ld", *currentScalePtr);
  send_status_message(message);

}

void cancel_calibration() {
  send_status_message("Calibration cancelled");
}


void read_and_send_data(){
  Serial.println("Debug test");
  // Read sensor data
  float thrust_value = thrust.get_units();
  float torque_value = 0.0f;
  float rpm_value = static_cast<float>(RPM);
  float voltage_value = 2.0f; // Replace with actual voltage reading
  float current_value = 5.0f; // Replace with actual current reading
  
  // Prepare sensor data payload
  uint8_t payload[20]; // 5 * 4 bytes for float
  memcpy(payload, &thrust_value, 4);
  memcpy(payload + 4, &torque_value, 4);
  memcpy(payload + 8, &rpm_value, 4);
  memcpy(payload + 12, &voltage_value, 4);
  memcpy(payload + 16, &current_value, 4);
  
  // Send sensor data
  send_binary_message(0x01, payload, sizeof(payload));
}


void send_binary_message(uint8_t message_type, const uint8_t* payload, uint32_t payload_length) {
  uint8_t prefix = 0xFF;
  uint16_t crc = calculate_crc(payload, payload_length);
  
  //DEBUG
  // Serial.print("Sending: ");
  // for (uint32_t i=0; i<payload_length; i++){
  //   Serial.print(payload[i], HEX);
  //   Serial.print(" ");
  // }
  // Serial.print("CRC: ");
  // Serial.println(crc, HEX);
  //DEBUG

  Serial.write(prefix);
  Serial.write(message_type);
  Serial.write((uint8_t*)&payload_length, 4);
  Serial.write(payload, payload_length);
  Serial.write((uint8_t*)&crc, 2);
}

void send_status_message(const char* message) {
  send_binary_message(0x03, (const uint8_t*)message, strlen(message));
}

bool receive_binary_message(uint8_t& message_type, uint8_t* payload, uint32_t& payload_length, uint32_t timeout) {
  uint32_t start_time = millis();
  while (millis() - start_time < timeout || timeout == 0) {
    if (Serial.available() >= 6) { // Minimum message size: prefix(1) + type(1) + length(4)
      uint8_t prefix = Serial.read();
      if (prefix != 0xFF) continue; // Invalid prefix, keep searching
      
      message_type = Serial.read();
      Serial.readBytes((uint8_t*)&payload_length, 4);
      
      // Wait for the full message to arrive
      while (Serial.available() < payload_length + 2) { // +2 for CRC
        if (millis() - start_time > timeout && timeout != 0) return false;
        delay(1);
      }

      Serial.readBytes(payload, payload_length);
      uint16_t received_crc;
      Serial.readBytes((uint8_t*)&received_crc, 2);
      
      uint16_t calculated_crc = calculate_crc(payload, payload_length);
      
      if (calculated_crc == received_crc) {
        // Debug print
        Serial.print("Received message: Type=");
        Serial.print(message_type, HEX);
        Serial.print(", Length=");
        Serial.print(payload_length);
        Serial.print(", Payload=");
        for (uint32_t i = 0; i < payload_length; i++) {
          Serial.print(payload[i], HEX);
          Serial.print(" ");
        }
        Serial.println();
        //Debug
        return true; // Valid message received
      }
    }
    
    if (timeout == 0) break; // Non-blocking mode, exit after one check
  }
  
  return false; // Timeout or no valid message
}

uint16_t calculate_crc(const uint8_t* data, uint32_t length) {
  crc.restart();
  crc.add(data, length);
  return crc.calc();
}


void perform_calibration(uint8_t sensor_type, float calibration_value) {
  HX711* sensor;
  const char* sensor_name;
  long* scale_ptr;

  if (sensor_type == CALIBRATION_THRUST) {
    sensor = &thrust;
    sensor_name = "Thrust";
    scale_ptr = &settings.thr_scale;
  } else if (sensor_type == CALIBRATION_THRUST) {
    sensor = &thrust;
    sensor_name = "Thrust";
    scale_ptr = &settings.thr_scale;
  } else {
    send_status_message("Invalid sensor type");
    return;
  }

  send_status_message("Starting calibration. Remove any load.");
  delay(2000);  // Give user time to remove load

  sensor->tare(10);
  send_status_message("Tare completed. Apply calibration load and send confirmation.");

  // Wait for confirmation to proceed
  uint8_t recv_message_type;
  uint8_t recv_payload[32];
  uint32_t recv_payload_length;
  if (receive_binary_message(recv_message_type, recv_payload, recv_payload_length, CALIBRATION_TIMEOUT)) {
    if (recv_message_type == 0x02 && recv_payload[0] == 1) { // Proceed with calibration
      double measured_value = sensor->get_value(10);
      *scale_ptr = measured_value / calibration_value;
      sensor->set_scale(*scale_ptr);
      
      // Save settings to EEPROM
      EEPROM.put(EEPROM_ADDRESS, settings);

      char message[64];
      snprintf(message, sizeof(message), "Calibration completed. Scale: %ld", *scale_ptr);
      send_status_message(message);
    } else {
      send_status_message("Calibration cancelled");
    }
  } else {
    send_status_message("Calibration timeout");
  }
}
