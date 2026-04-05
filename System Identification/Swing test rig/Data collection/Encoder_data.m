a = arduino('COM13','Uno','Libraries','rotaryEncoder');
encoder = rotaryEncoder(a,'D2','D3');

samplingFrequency = 20; %Hz
t_f = 20; %s

rate = rateControl(samplingFrequency);

resetCount(encoder);
data = zeros(t_f*samplingFrequency,2);
periodOut = zeros(t_f*samplingFrequency,1);

fprintf("Data collection started\n")

for i = 1:(t_f*samplingFrequency)
    periodOut(i) = rate.LastPeriod;
    [data(i,2), data(i,1)] = readCount(encoder);
    waitfor(rate);
end

clear a
clear encoder

t = data(:,1);
orientation = data(:,2)/4;

plot(t, orientation);