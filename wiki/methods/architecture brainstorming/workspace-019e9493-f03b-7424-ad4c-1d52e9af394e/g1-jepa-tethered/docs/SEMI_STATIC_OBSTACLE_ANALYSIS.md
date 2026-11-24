# Deep Dive: The "Semi-Static Chair" Scenario

A chair standing in front of a robot is a notoriously difficult edge case in Dynamic SLAM. It is **semi-static**: it is not a walking human (so standard pedestrian trackers ignore it), but it isn't a solid wall either (it has thin legs that are hard to see, and it can be easily bumped or moved by a human).

Here is exactly how our 3-loop tethered architecture processes the chair, explicitly highlighting the execution speeds (Hz) and latencies of each sub-system.

---

### 1. The Perception Layer (What the Sensors Do)
* **RealSense D435i (Depth/RGB) [30 Hz | ~15ms latency]:** As the robot approaches, the RealSense captures the dense geometry of the chair at close range (0.5m - 3m). Because chairs have thin legs, the active IR stereo depth is critical here.
* **Livox Mid-360 (LiDAR) [10 Hz | ~50ms latency]:** The LiDAR sweeps the room. Because of its non-repetitive Rhodonea pattern, it eventually catches the thin chair legs and the backrest, confirming the depth camera's readings.
* **The "Masking" Bypass (YOLOv11 / LV-DOT) [30 Hz | <20ms latency]:** The Orin NX runs YOLOv11-pose and the LV-DOT tracker. Because a chair is *not* a human, no semantic bounding box is generated. Therefore, the chair bypasses the Dynamic Masking filter. The system assumes it is part of the static environment.

### 2. The Geometric Layer (How the Map Reacts)
* **GPU Elevation Grid [20 Hz | 12ms latency]:** The RealSense and LiDAR points belonging to the chair are projected downward into the 2.5D footstep grid running on the RTX 5090. The seat and legs register as massive spikes in the `Step Height (h > 15cm)` metric. The cells underneath the chair are instantly marked as `KINEMATIC_LIMIT` (non-traversable).
* **LCD-Splat / AG-SLAM [5 Hz | 150ms latency]:** Operating asynchronously on the RTX 5090, the chair is baked into the global 3D Gaussian Splat map. It is now treated as a permanent structural obstacle in the room.

### 3. The Cognitive Layer (What the VLM "Thinks")
* **Cosmos 3 Nano VLM [1 Hz | 850ms latency]:** The VLM on the RTX 5090 receives the Ego-RGB feed and the top-down LCD-Splat render.
  * **Semantic Grounding:** The VLM recognizes the visual tokens as a "Chair". Unlike the geometric map (which just sees a block of pixels), the VLM understands its *affordances*. It knows a chair is lightweight, movable, and meant for sitting.
  * **Intent Generation:** 
    * *If the goal is purely navigation:* The VLM generates a macro-route: `{"action": "AVOID", "target_coordinates": [x, y]}` routing the robot a safe 0.5m distance away from the chair.
    * *If the goal is interaction (e.g., "clear the path"):* The VLM outputs a route directly to the backrest of the chair and queues a manipulation skill for the robot's arms to push it.

### 4. The Action Layer (MPPI & CBF Execution)
* **MPPI Trajectory Planning [30 Hz | 30ms latency]:** The MPPI planner receives the VLM's macro-route. It samples thousands of possible continuous walking trajectories. It uses the 2.5D Elevation Grid as its costmap, ensuring no trajectory attempts to place a foot on the chair legs. It selects the smoothest path around it.
* **What if the chair gets bumped?** Let's say a human suddenly bumps the chair while the robot is walking past it, pushing it directly into the robot's shin.
  * **Epipolar Geometry Checker [15 Hz | ~40ms latency]:** Instantly realizes the chair's visual features are violating static geometry constraints. It flags the chair as "Dynamic" and temporarily rips it out of the LCD-Splat map.
  * **Elevation Grid [20 Hz | 12ms latency]:** Updates almost instantly, showing a new non-traversable spike directly in front of the robot's swinging foot.
  * **Control Barrier Function (CBF) [500 Hz | 2ms latency]:** Running natively in the Whole-Body Controller on the Orin NX, the CBF catches the impending collision in mere milliseconds. It physically overrides the MPPI planner, forcing the robot to immediately abort the forward step and plant its foot sideways to maintain balance, avoiding the moving chair leg.

---

### Why the 3-Loop Architecture is Mandatory for this Scenario:
If we relied solely on the VLM to avoid the chair, the robot would crash, because the VLM operates at **1 Hz (850ms latency)**. By the time the VLM realizes the chair was bumped, the robot has already taken 2 full steps and tripped over it.

This perfectly demonstrates the required split:
1. **Semantic Loop (1 Hz / 850ms):** Understands it's a chair and decides to walk around it.
2. **Predictive Loop (30 Hz / 30ms):** Plans the exact footstep trajectory to not step on the legs.
3. **Reactive Loop (500 Hz / 2ms):** Saves the robot from falling when the chair is unexpectedly shoved into its path.
