import serial, csv

port = 'COM13'
pollPeriod = 10 #ms
testDuration = 30 #s

testSamples = int(testDuration*1000/pollPeriod) #ms
ser = serial.Serial(port, 115200)

t = []
angle = []
samples = 0

for i in range(50):
    data = ser.readline().decode('utf-8').strip().split(',')

for i in range(testSamples):
    data = ser.readline().decode('utf-8').strip().split(',')
    if i == 0:
        t0 = int(data[0])
    t.append(float(int(data[0])-t0)/1000)
    angle.append(float(data[1]))

    print(f'Time true (s): {float(int(data[0])-t0)/1000},\t Time (s): {i*pollPeriod/1000} \t Angle: {data[1]}')

with open('knownMassTest.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    for t, angle in zip(t, angle):
        writer.writerow([t, angle])