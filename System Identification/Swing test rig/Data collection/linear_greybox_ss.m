function [A, B, C, D] = linear_greybox_ss(m,g,l,I_tot,c,Ts)
A = [0 1; (-m*g*l/I_tot), (-c/I_tot)];
B = zeros(2,0);
C = [1 0];
D = zeros(1,0);
end

