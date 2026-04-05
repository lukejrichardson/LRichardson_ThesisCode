Ts_FB = 1/500; % Rate that the states are fedback to controller

g = 9.81; % m/s^2

m = 0.650; % kg

d = 0.156; % m

h = 0; % m


pos_i = [0 0 0]'; % initial position (m)

% discrete butterworth gyro filter coefficients
% w_c = 40 Hz, t_s = 0.001s
% continuous tf: ((40*2*pi)^2) / (s^2 + sqrt(2)*40*2*pi*s + (40*2*pi)^2)
% discrete tf: (0.02801*z + 0.02487) / (z^2 - 1.648 + 0.7009)
gyro_filt_num = [0.02801 0.02487];
gyro_filt_den = [1 -1.648 0.7009];

% Uncertain parameters

J_xx_u = ureal('J_xx', 0.001630, 'Percentage', 3);
J_yy_u = ureal('J_yy', 0.002156, 'Percentage', 4);
J_zz_u = ureal('J_zz', 0.003281, 'Percentage', 3);

J_u = [J_xx_u   0 0;
        0  J_yy_u  0;
        0  0  J_zz_u]; % kg.m^2


Tc_m_u = ureal('F_tc', 0.033, 'Percentage', 18);
Td_m_u = ureal('F_td', 0.0349, 'Percentage', 26);

cmd2thrust_u = ureal('cmd2thrust', 7.58*10^(-4), 'Percentage', 5);

cmd2torque_u = ureal('cmd2torque', 8.75*10^(-6), 'Percentage', 5);

% initialise uncertain parameters to nominal values

J = J_u.NominalValue;

Tc_m = Tc_m_u.NominalValue*ones(4,1);

Td_m = Td_m_u.NominalValue*ones(4,1);

cmd2thrust = cmd2thrust_u.NominalValue*ones(4,1);

cmd2torque = cmd2torque_u.NominalValue*ones(4,1);

% import and initialise controllers to PDESO

thrust2cmd = 1/cmd2thrust_u.NominalValue;
yaw2thrust = cmd2thrust_u.NominalValue/(4*cmd2torque_u.NominalValue);

load("AttitudeControllers.mat")
load("PositionControllers.mat")
AttController = "PDESO";
PosController = "PDESO";