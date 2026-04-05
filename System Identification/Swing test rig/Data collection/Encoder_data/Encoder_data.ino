volatile long temp, time, samples = 0, counter = 0; //This variable will increase or decrease depending on the rotation of encoder
volatile uint16_t timeOfPoll = 0;
static uint8_t pollPeriod = 50; //ms
static uint32_t duration = 20000; //ms

void setup() {
  Serial.begin (9600);
  pinMode(2, INPUT_PULLUP); // internal pullup input pin 2 
  
  pinMode(3, INPUT_PULLUP); // internal pullup input pin 3
  //Setting up interrupt
  //A rising pulse from encodenren activated ai0(). AttachInterrupt 0 is DigitalPin nr 2 on moust Arduino.
  attachInterrupt(digitalPinToInterrupt(2), ai0, RISING);
  

  //B rising pulse from encodenren activated ai1(). AttachInterrupt 1 is DigitalPin nr 3 on moust Arduino.
  //attachInterrupt(1, ai1, RISING);
  attachInterrupt(digitalPinToInterrupt(3), ai1, RISING);
  }
   
  void loop() {
  // Send the value of counter
  //if( counter != temp ){
  time = millis();
  if(time-timeOfPoll >= pollPeriod){
    timeOfPoll = millis();
    samples ++;
    Serial.print (counter);
    Serial.print (',');
    Serial.print (time);
    Serial.print ('\n');
  }
  if (samples > duration/pollPeriod){
    exit(0);
  }
  //temp = counter;}
  }
   
  void ai0() {
  // ai0 is activated if DigitalPin nr 2 is going from LOW to HIGH
  // Check pin 3 to determine the direction
  if(digitalRead(3)==LOW) {
  counter++;
  }else{
  counter--;
  }
  }
   
  void ai1() {
  // ai0 is activated if DigitalPin nr 3 is going from LOW to HIGH
  // Check with pin 2 to determine the direction
  if(digitalRead(2)==LOW) {
  counter--;
  }else{
  counter++;
  }
  }