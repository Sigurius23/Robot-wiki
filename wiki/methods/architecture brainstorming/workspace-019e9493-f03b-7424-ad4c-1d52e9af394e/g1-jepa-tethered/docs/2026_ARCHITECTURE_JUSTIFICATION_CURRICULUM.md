# The Curriculum of Complexity: Architectural Justification

To understand *why* the Unitree G1 requires our complex, multi-loop tethered architecture (SLAM + VLMs + Dynamic Masking + CBFs), we must test it against a "Curriculum of Complexity". 

Instead of comparing a basic stack to a complex stack, this document evaluates **4 Distinct Architectural Paradigms** across 8 escalating scenarios, demonstrating exactly when and why each paradigm catastrophically fails.

### The 4 Paradigms
1. **Classical Robotics (Zero-AI):** Standard ROS2 Nav2 stack, 2D Lidar, Costmaps. (Rigid, fast, zero semantic understanding).
2. **Pure End-to-End AI (VLA/VLM):** Pixels-to-actions via giant neural networks. (High semantic reasoning, black-box, physically unsafe, high latency).
3. **The G1-Tethered Hybrid (Our Current Stack):** The 3-Loop split (Orin NX + RTX 5090). (Balances safety, speed, and cognition).
4. **The "Thor" Future-State:** Unlimited onboard compute (e.g., dual NVIDIA Thor boards). (Running unquantized 34B parameter models natively at 30Hz).

---

## Level 1: Empty Room, Visible Goal (Line-of-Sight)
**The Task:** Walk 5 meters forward across an empty room to reach a visible blue marker.

* **Classical:** **Pass.** Uses simple PID control on camera centroids. Extremely fast, mathematically perfect.
* **End-to-End AI:** **Pass.** The VLA maps pixels directly to walking gaits. High latency (~800ms) makes it slightly wobbly, but it succeeds.
* **Tethered Hybrid:** **Pass.** VLM sees goal, MPPI executes a straight line.
* **Thor:** **Pass.** Overkill.

---

## Level 2: The Static Isolated Obstacle (The Chair)
**The Task:** Walk forward but maneuver around a semi-static chair in the path.

* **Classical:** **Pass.** 2D Lidar sees the chair legs, Nav2 costmap inflates the obstacle, local planner routes around it.
* **End-to-End AI:** **Struggle/Fail.** The network understands it's a chair, but because the latency is so high, it struggles to precisely plan foot placements. It frequently clips the chair legs due to "hallucinating" physical boundaries.
* **Tethered Hybrid:** **Pass.** RealSense + Elevation Grid maps the precise 3D geometry of the legs at 20Hz. MPPI routes the feet flawlessly.
* **Thor:** **Pass.** 30Hz VLA natively plans perfect kinematic avoidance.

---

## Level 3: The Static Maze (Out of Line-of-Sight)
**The Task:** Navigate through a complex, multi-room office to find "Room 402". The goal is not visible from the start.

* **Classical:** **Struggle/Fail.** Can navigate if pre-mapped, but fails entirely at semantic routing ("What is Room 402?"). If the office has 3D overhangs (tables, stairs), the 2D Lidar fails and the robot hits its head.
* **End-to-End AI:** **Fail.** VLMs lack spatial object permanence. Without a persistent geometric map (SLAM), the network forgets what it saw 30 seconds ago, wanders down dead ends, and gets trapped in loops.
* **Tethered Hybrid:** **Pass.** 3D Livox LiDAR + AG-SLAM / 3D Gaussian Splatting provides infinite memory. The VLM performs semantic routing ("Go left at the water cooler"), and MPPI follows the global SLAM path.
* **Thor:** **Pass.** Same as hybrid, but calculated entirely onboard.

---

## Level 4: The Unpredictable Dynamic Object
**The Task:** A dog suddenly runs directly in front of the robot's swinging foot.

* **Classical:** **Fail.** Nav2 local planners (DWA/TEB) take ~100ms to react. The robot trips over the dog and falls.
* **End-to-End AI:** **Catastrophic Fail.** The ~800ms inference latency means the robot doesn't even realize the dog is there until it is already falling on the floor.
* **Tethered Hybrid:** **Pass.** The 500Hz Control Barrier Function (CBF) on the Orin NX acts as a mathematical safety floor. It physically aborts the footstep in 2ms, planting the foot sideways to save the robot before the VLM even registers the event.
* **Thor:** **Pass.** The 30Hz network might catch it, but it still relies on a low-level CBF to prevent kinematic failure.

---

## Level 5: The Semi-Static Environment
**The Task:** Traverse an area where a heavy door was opened and a couch was moved *after* the SLAM map was originally built.

* **Classical:** **Fail.** The robot blindly trusts the old map, thinks the door is closed, and refuses to enter the room. If forced, it creates permanent "ghost" pixels on the map.
* **End-to-End AI:** **Pass.** It doesn't rely on a map, so it just reacts to what it currently sees and walks through the open door.
* **Tethered Hybrid:** **Pass.** Uses Epipolar Geometry Consistency and Probabilistic Ray-Casting. The SLAM pipeline instantly detects that the visual features of the couch moved, strips them from the Splat map, and organically inpaints the new geometry.

---

## Level 6: Sparse Crowd Navigation
**The Task:** Navigate a long hallway while 2-3 people walk in the opposite direction.

* **Classical:** **Fail.** Standard dynamic SLAM treats humans as moving brick walls. The robot stops constantly, violently recalculating paths every time a human moves an inch.
* **End-to-End AI:** **Struggle.** It can weave through them semantically, but lacks precision footstep planning, making it look jerky and dangerous around humans.
* **Tethered Hybrid:** **Pass.** YOLOv11-pose + LV-DOT Tracker explicitly tracks the humans. The MPPI planner receives velocity vectors and predicts human trajectories, gracefully routing the robot *behind* them without ever stopping.

---

## Level 7: Dense Crowd with Flow (The Conference Break)
**The Task:** Traverse a highly congested fair floor where attendees are moving in multiple opposing directions.

* **Classical:** **Catastrophic Fail.** The "Freezing Robot Problem". The costmap inflates around every human. The robot concludes there is 0% traversable space, throws a "No Path Found" error, and freezes permanently.
* **End-to-End AI:** **Fail.** The VLM hallucinates a path but cannot execute it safely in real-time, bumping into attendees.
* **Tethered Hybrid:** **Pass.** The Dual-Pipeline Split completely masks the crowd from the SLAM map. We swap MPPI for **π₀.₅ Flow Matching**. The robot stops treating humans as static obstacles and instead learns the "fluid dynamics" of the crowd, naturally weaving through the gaps like a pedestrian.

---

## Level 8: Social Navigation & Interaction (The Final Boss)
**The Task:** Navigate the fair, identify someone who looks interested, approach them, and hand them a flyer.

* **Classical:** **Complete Failure.** Has absolutely zero concept of social dynamics, gaze, or human intent.
* **End-to-End AI:** **Struggle.** The VLM can identify an interested person, but lacks the architectural flexibility to run simultaneous dialogue models and safety planners.
* **Tethered Hybrid:** **Pass.** 
  1. The Cosmos VLM parses Gaze/Body Language at 1Hz to find an "Approachable" target.
  2. The robot triggers a **Context Mode Swap** on the RTX 5090, paging out the SLAM mapping models to load the Omni-LLM.
  3. The robot routes to the person (MPPI), raises its arm (WBC), and initiates real-time dialogue (Omni-LLM), all while the 500Hz CBF ensures it doesn't step on their toes.
* **Thor:** **Pass.** Achieves the same result, but without needing the Context Mode Swap, as it has 64GB of unified memory onboard to hold all models simultaneously.

---

### Conclusion
By scaling the complexity, we definitively prove that a pure classical stack fails at Level 3 (Cognition), a pure AI stack fails at Level 4 (Physics/Latency), but the **Tethered Hybrid Architecture** scales perfectly through Level 8 by assigning high-latency semantics to the GPU cloud, and low-latency survival physics to the edge.
