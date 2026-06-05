# Sim-to-Real Transfer Validation Strategy (G1-JEPA)

Before physical deployment of the Master Tethered Architecture, the following three-stage validation pipeline must be completed to mitigate risks of catastrophic hardware failure.

## 🛠 Stage 1: "Digital Twin" Photorealistic Stress Tests
*   **Environment:** Isaac Gym / NVIDIA Isaac Sim.
*   **Method:** Use the **3D Gaussian Splatting (3DGS)** captures of the actual deployment lab to create a high-fidelity "Digital Twin."
*   **Validation:** 
    *   **Tether Stress:** Simulate the mechanical leash dynamics and verify that the MPPI $\theta_{yaw}$ penalty prevents leg entanglement in the virtual CAT6.
    *   **Perception Latency:** Inject 40ms of simulated network jitter and verify that the `TrajectoryBuffer` handles kinematic decay without the robot tripping.
    *   **Acoustic NLOS:** Test "Blind Corner" scenarios where the robot must slow down based purely on synthetic audio footsteps before the person is visually visible.

## 🧪 Stage 2: Hardware-in-the-Loop (HIL) Resource Saturation
*   **Environment:** Offboard RTX 5090 Laptop + Onboard G1 Orin NX (Robot Suspended).
*   **Method:** Run the full JEPA stack with the robot suspended on a gantry.
*   **Validation:**
    *   **OOM Handling:** Manually bloat the 4D Voxel Map with complex geometry and verify the `DynamicVRAMPlanner` throttles samples without crashing.
    *   **Thermal Profiling:** Run at 40W "Super Mode" for 60 minutes. Monitor Orin NX and RTX 5090 junctions for thermal throttling that could drop the planning frequency below 40Hz.
    *   **Watchdog Trip:** Hard-sever the Gigabit Ethernet cable while the G1 is executing a 1.5 m/s treadmill gait. Verify the 500ms decay buffer results in a stable, zero-velocity stand.

## 🏃 Stage 3: Shadow Mode Field Tests
*   **Environment:** Physical Lab with a Human Safety Operator.
*   **Method:** The G1 walks using traditional FAST-LIO2 / SLAM while the JEPA stack runs in "Shadow Mode" (calculating but not executing actions).
*   **Validation:**
    *   **Divergence Analysis:** Compare the JEPA "Hallucinated Trajectory" with the actual SLAM path.
    *   **False Positive Audit:** Log instances where Acoustic-JEPA triggered a yield for a sound that was not a hazard.
    *   **Tether Payout:** Verify the motorized spool maintains constant tension (no slack/snags) during 360-degree rotations.

---

### **Success Criteria for Physical Deployment**
1.  **Zero OOM Crashes** over 10 hours of "Shadow Mode" in cluttered environments.
2.  **Mean Tracking Error** between V-JEPA 2 predictions and actual FAST-LIO2 states < 5cm.
3.  **Mechanical Tension** remains within 5N - 20N range throughout all 43-DOF articulation tests.
