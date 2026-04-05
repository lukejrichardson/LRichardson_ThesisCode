  #define INPUT_ENCOD_A    2                                  // *** MEGA PIN2 (***=adapt with input pin)
  #define INPUT_ENCOD_B    3                                  // *** MEGA PIN3
  #define SignalA          B00000100                          // *** MEGA PIN2 = PORT_E  bit4 = B00010000
  #define SignalB          B00001000                          // *** MEGA PIN3 = PORT_E  bit5 = B00100000
  #define SignalAB         B00001100                          // *** both signals
  volatile int             ISRencodPos;                       // encoder position
  int                      encodLastPos;                      // previous position
  byte                     LastPort8 = SignalA;               // previous A/B state
  volatile uint16_t        samples = 0;
  volatile uint16_t        timeOfPoll = 0;                    //ms
  static uint8_t           pollPeriod = 10;                   //ms
  static uint32_t          time, duration = 20000;            //ms  



void setup(void) {                                            //
  pinMode(2, INPUT_PULLUP);                       //
  pinMode(3, INPUT_PULLUP);                       //
  attachInterrupt(digitalPinToInterrupt(2), ExtInt, CHANGE);
  attachInterrupt(digitalPinToInterrupt(3), ExtInt, CHANGE);
  Serial.begin(115200);                                       // fast fast fast !
}                                                             //


void ExtInt() {                                               /// OPTICAL ENCODER ext interrupt pin X, Y
     byte Port8  =  PIND & SignalAB;                          // *** PINE (PORT INPUT E)  ***for Mega***
      LastPort8 ^=  Port8;                                    //                                      
  if (LastPort8 & SignalA)   ISRencodPos++;                   // Rotation -> {ISRencodPos++; Sense = 1;}
  if (LastPort8 & SignalB)   ISRencodPos--;                   // Rotation <- {ISRencodPos--; Sense = 0;}
  if (    Port8 && (Port8 != SignalAB)) Port8 ^= SignalAB;    //                              (swap A-B)
      LastPort8  =  Port8;                                    //                  mieux vaut faire court
}                                                             //


void loop(void) {                                             /// MAIN LOOP
  noInterrupts();                                             //
    float encodPosition = float(ISRencodPos)/4;               //
  interrupts();                                               //

  time = millis();
  if (time-timeOfPoll >= pollPeriod) {                        // when the encoder change,
    timeOfPoll = millis();
    samples++;
    Serial.print(time);
    Serial.print(',');
    Serial.println(encodPosition);
  }                                                           //

  if (samples > duration/pollPeriod){
    //exit(0);
  }
}