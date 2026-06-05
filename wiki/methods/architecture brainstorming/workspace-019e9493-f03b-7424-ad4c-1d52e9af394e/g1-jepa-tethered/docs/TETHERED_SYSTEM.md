# Tethered System Engineering

## 1. The Mechanical Leash
- **Top-Mounted Gigabit Slip Ring:** Allows for 360-degree infinite yaw without cable twisting.
- **Motorized Active Tension Spool:** Monitors cable slack and maintains 5N-20N of tension.

## 2. Communication Protocol
- **Gigabit Ethernet:** <1ms latency for the 40Hz planner loop.
- **Tether State Vector:** x = [theta_yaw, L_payout, Tension].

## 3. Entanglement Avoidance
- **Unwrapped Yaw Penalty:** lambda * (theta_yaw^2) in the MPPI cost function.
- **Self-Winding Awareness:** The world model predicts cable trajectory to avoid leg interference.
