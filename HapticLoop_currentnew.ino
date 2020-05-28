 // HapticLoop_current.ino
// (C) Jake Carducci 2020
// Initialization Header
// PWM pins (DO NOT ALTER)
int pinArray[] = {
  7,5,4,3,2 
};
// Stores duration value from PC command
byte vib_duration = 0;
// Stores timestamp for timer comparison
unsigned long vib_timer[5] = {};
const int mag_length = 3;
byte inputArray[mag_length] = {};         // a String to hold incoming data
bool arrayComplete = false;  // whether the string is complete
bool serialMonitor = false;
int i = 0;
int j=0;
int A;
int pinCnt = 5;
const int ledMain = 13;
bool ledState = true;
bool allInToggle = false;
bool onMotor = false;
// Settings Header
// Length of routine delays
int timer = 1000;   
// Activate routine to pulse each motor sequentially
bool autoMode = false;
// Activate routine to pulse all motors at once
bool allInMode = false;
// Program start
void setup() {
  // initialize serial port for PC communication:
  Serial.begin(9600);
  // set pins specified in "pinArray[]" to accept output stimulating commands:
  for (int thisPin = 0; thisPin < pinCnt; thisPin++) {
    pinMode(pinArray[thisPin], OUTPUT);
  }
  // set the status LED to accept output light commands, and start it in the off state
  pinMode(ledMain, OUTPUT);
  digitalWrite(ledMain,LOW);
}
void loop() {
   Serial.print(A, HEX);
    // if "autoMode" is set to true in the settings header, the microcontroller will pass through each entry of "pinArray[]" and turn on the corresponding pin, wait for "timer" seconds as specified in the settings header, turn off the pin, and move to the next entry
  if (autoMode) {
    // iterate over the pins:
    for (int thisPin = 0; thisPin < pinCnt; thisPin++) {
      // turn the pin on:
      digitalWrite(pinArray[thisPin], HIGH);
      delay(timer);
      // turn the pin off:
      digitalWrite(pinArray[thisPin], LOW);
      // If the microcontroller receives a command from the PC, it interrupts the array progression
      if (Serial.available()){
        break;
      }
    }
    // if "allInMode" is set to true in the settings header, the microcontroller will turn on every pin specified in "pinArray[]", wait for "timer" seconds, and turns them off
  } else if (allInMode) {
    for (int thisPin = 0; thisPin < pinCnt; thisPin++) {
      // turn the pin on:
      if (allInToggle){
        digitalWrite(pinArray[thisPin], HIGH);
      } else {
        // turn the pin off:
        digitalWrite(pinArray[thisPin], LOW);
      }
      // If the microcontroller receives a command from the PC, it interrupts the array progression
      if (Serial.available()){
        break;
      }
    }
    // Delays either routine for "timer" seconds between for loops
     delay(timer);
    // Toggles the state of all motor pins
    allInToggle = !allInToggle;
  }
    // Lights up the LED
  if (ledState){  
    //digitalWrite(ledMain,HIGH);
  } else {
    //digitalWrite(ledMain,LOW);
  }
    // Toggles the LED state for every loop routine
  ledState = !ledState;
    // If the microcontroller gets a complete command from the PC, it will pull the duration of the command and the intensities for each motor. After sending a confirmation message back to the PC, the microcontroller turns on the targeted motors
  if (arrayComplete) {
    
    vib_duration = 2; //default 2 seconds
    Serial.write(inputArray,mag_length);
    if (inputArray[2] == 1) {
    
      activateMotor((int)inputArray[1]);
     
      //Serial.print(A, HEX);
      //delay(2000);
     
      //disableMotor((int)inputArray[1]);
      // Timestamp in UNIX time for start of vibration
      //vib_timer[inputArray[1]] = millis();
    }
    else if (inputArray[2] == 0 ){
      
    
     disableMotor((int)inputArray[1]);
    }
    //digitalWrite(pinArray[inputNum-1], LOW);
    arrayComplete = false;
  }
 //for (j=0;j<5;j++){
    // After the duration of the command has elapsed (the difference between millis timestamps is greater than the specified duration), the motors are disabled
  //if (millis() - vib_timer[j] > 1000 * vib_duration && onMotor){
      
   //  disableMotor(j);
 // }
//  }
}

// Turns on each motor to an intermediate intensity specified by the PC command
void activateMotor(int f){
analogWrite(pinArray[f],100);
onMotor = true;
digitalWrite(ledMain,HIGH);
  
}
// Turns off all motors by setting intensities to zero
void disableMotor(int f){
analogWrite(pinArray[f],0);
onMotor = false;
digitalWrite(ledMain,LOW);
}
/*
  SerialEvent occurs whenever a new data comes in the hardware serial RX. This
  routine is run between each time loop() runs, so using delay inside loop can
  delay response. Multiple bytes of data may be available.
*/
void serialEvent() {
  while (Serial.available()) {
    // get the new byte:
    byte inByte = (byte)Serial.read();
    // add it to the inputString:
    inputArray[i] = inByte;
    i += 1;
    // if the incoming character is a newline, set a flag so the main loop can
    // do something about it:
    if (i == mag_length) {
      arrayComplete = true;
  
      i = 0;
    }
  }
}
