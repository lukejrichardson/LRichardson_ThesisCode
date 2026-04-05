function [dx, y] = nl_greybox_ss(t, x, u, I, c1, c2, m, g, l, varargin)

theta = x(1);
dtheta = x(2);

dx = [dtheta;    ... 
      (- c1*dtheta - (c2/10000000)*(dtheta^2)*sign(dtheta) - m*g*l*sin(theta))/(I)];  % ddtheta

y = theta;