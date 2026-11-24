# 2026/2027 State-of-the-Art: 3D Environment Mapping, Dynamic SLAM & Terrain Traversability

**Target Platform:** Unitree G1 EDU  
**Compute Architecture:** Tethered Setup (Onboard: NVIDIA Jetson Orin NX 16GB | Offboard: RTX 5090 24GB Laptop)  
**Sensor Suite:** Livox Mid-360 (3D LiDAR), Intel RealSense D435i (Depth/RGB), Head IMU  

---

## 1. System Architecture & Dual-Pipeline Integration Strategy

In humanoid robotics, coupling high-frequency pedestrian tracking with low-frequency static environment mapping into a single algorithm inevitably compromises both. The 2026 standard for platforms like the Unitree G1 enforces a **strict dual-pipeline architecture**:

### Static-Dynamic Decoupling
The core principle is **Semantic-Geometric Masking**. Before any point cloud data is fed into the map structure (occupancy grid or 3D Gaussian Splats), it passes through a masking filter. The tracking pipeline (running YOLOv11-pose and LV-DOT on the Orin NX) identifies the precise 3D bounding boxes of all moving pedestrians in the LiDAR frustum. These dynamic points are explicitly **erased** from the LiDAR stream. 
- **Dynamic Stream (Masked Points):** Routed to the VLM (Cosmos) and MPPI for crowd avoidance and social interaction.
- **Static Stream (Cleaned Geometry):** Routed to the SLAM and Terrain Mapping threads to build the persistent environment representation.

### Sensor Synergy (Livox Mid-360 + RealSense D435i)
- **Livox Mid-360 (Non-Repetitive Rhodonea Scanning):** Provides 360° FOV, mapping walls, distant obstacles, and structural boundaries up to 40m indoors. Its non-repetitive scan pattern is ideal for rapidly densifying static maps.
- **RealSense D435i (Stereo Depth):** Pointed downwards/forwards, providing ultra-dense, high-resolution short-range (0.3m–3m) depth geometry specifically for bipedal footstep planning and immediate obstacle clearance.

### Spatiotemporal Synchronization & Deskewing
Because the G1's torso sways violently during walking, LiDAR scans suffer from motion distortion (skew). We rely on the **FAST-LIO2** front-end. FAST-LIO2 tightly couples the 1000Hz IMU with the 10Hz LiDAR sweeps, using an Iterated Extended Kalman Filter (IEKF) to propagate the robot's state and deskew the point cloud at the exact microsecond each laser pulse fired, ensuring the map remains crisp regardless of gait instability.

---

## 2. Dynamic SLAM & The Complexities of Ghosting Mitigation (2026/2027 SOTA)

When pedestrians walk through a traditional SLAM map, they leave "ghost" trails of points that the robot later interprets as solid walls. However, simply removing dynamic entities (like humans) from a mapping pipeline creates a new set of complex problems:

### The Pitfalls of "Blind Masking"

1. **Feature Depletion and Tracking Loss:** If a pedestrian walks close to the camera or LiDAR, their body mask can occupy $40\%\text{–}70\%$ of the sensor's field of view. If a SLAM algorithm simply erases all points inside that bounding box, it starves the visual-inertial odometry (VIO) engine. In feature-sparse corridors, this sudden feature depletion causes the SLAM system to lose localization tracking entirely.
2. **The "Semi-Static" Object Dilemma:** Humans interact with the physical world (pushing a chair, opening a door). If a system blindly erases everything associated with human activity, it deletes valuable static structural cues; if it retains them incorrectly, it bakes permanent phantom obstacles into the global map.
3. **Map Holes and Occlusion Infill:** When a person moves away, they reveal a wall or ground space that was previously hidden. The mapping system must seamlessly "infill" this newly exposed region without leaving geometric tears, holes, or boundary artifacts in the elevation or surface mesh.

---

### How Modern Frameworks Solve These Problems

To prevent these issues from degrading spatial perception, researchers utilize several tightly coupled approaches running concurrently on the RTX 5090:

#### A. Multi-View Epipolar Geometry Verification
Instead of automatically deleting every pixel or point cloud return inside a human segmentation mask (such as a YOLOv11-pose output), modern systems (like GARAD-SLAM) use **Epipolar Geometry Consistency Verification**. 

* The system computes the fundamental matrix $\mathbf{F}$ between consecutive frames and projects epipolar lines.
* If a feature point $\mathbf{p}$ inside a human bounding box satisfies the epipolar constraint (meaning it actually belongs to a static background wall visible behind the person's arm), it is **retained**. The constraint states that the projection on the current frame $\mathbf{x}_c$ and previous frame $\mathbf{x}_p$ must satisfy:
$$ \mathbf{x}_c^T \mathbf{F} \mathbf{x}_p = 0 $$
* If the residual $e = |\mathbf{x}_c^T \mathbf{F} \mathbf{x}_p| > \tau$ (meaning it is physically moving), it is flagged as dynamic and filtered out, preserving static background features even in dense crowds.

#### B. Probabilistic Ray-Casting & Radiance Field Inpainting
To handle newly exposed spaces when a human moves:
* **Occupancy Grids:** Systems update voxel states using log-odds probability updates. When a laser pulse from the Livox Mid-360 passes through a space previously occupied by a human and strikes a wall behind them, the ray-casting algorithm lowers the occupancy probability of the intermediate voxels to zero. The "phantom" human points fade out probabilistically.
* **3D Gaussian Splatting (3DGS) SLAM:** Background geometry is modeled as continuous 3D Gaussian primitives. Moving humans are handled by assigning them transient confidence weights. When the person steps away, newly observed visual rays instantly update the underlying background Gaussians, naturally inpainting the background.

#### C. Probabilistic Motion Influence Fields (Active SLAM)
To prevent feature depletion, active SLAM planners utilize **Motion Influence Fields**. The robot models the velocity vectors and directional uncertainties of nearby tracked pedestrians as anisotropic Gaussian fields. If the planner predicts that a pedestrian's movement will mask too many static background features along the current camera heading, the active SLAM system adjusts the robot's gaze or path slightly to keep feature-rich static background geometry in view.

#### D. Joint State Optimization via Parallel Execution
Rather than discarding dynamic data, modern architectures maintain a **Joint Dual-Representation State**:
1. **The Mapping Thread (AG-SLAM/LCD-Splat)** receives only points verified as static/environment features, maintaining a clean map for bipedal footstep planning.
2. **The Tracking Thread (LV-DOT)** receives the dynamic human points, tracking them as moving kinematic obstacles (with positions, velocities, and body headings).

By running these pipelines in parallel, the local path planner superimposes the active human trajectories onto the clean static map in real time.
---

## 3. Terrain Traversability & Elevation Mapping for Humanoid Locomotion

Bipedal locomotion requires specialized terrain analysis. A humanoid cannot treat the world as a 2D costmap; it must know the exact slope and height of the ground beneath its feet.

### GPU-Accelerated 2.5D Elevation Mapping
The cleaned static point cloud (primarily from the RealSense D435i) is projected into a 2.5D Elevation Grid centered on the robot. This grid operates on the GPU (RTX 5090) and computes three metrics per cell (e.g., $5\text{cm} \times 5\text{cm}$ resolution):
1. **Step Height ($h$):** The absolute $Z$-variance.
2. **Slope Gradient ($\nabla h$):** Computed via surface normal estimation using PCA on the local point neighborhood.
3. **Terrain Roughness ($\sigma$):** The standard deviation of heights within the cell.

If $h > 15\text{cm}$ or $\nabla h > 25^\circ$, the cell is marked as non-traversable (KINEMATIC_LIMIT). The Whole-Body Controller (WBC) uses this map to plan viable $X, Y, Z$ foot placements.

### Environmental Variations
- **Indoor (Low-Lux):** The RealSense D435i relies entirely on its active IR projector, which works flawlessly. Livox LiDAR is completely unaffected by ambient light.
- **Outdoor (Direct Sunlight >80,000 lx):** The RealSense's active IR projector is completely washed out by the sun, effectively blinding the depth camera. The system must dynamically shift reliance entirely to the Livox Mid-360 LiDAR for terrain mapping, accepting a slightly sparser footstep map.

---

## 4. Detailed Model Hardware & Computational Profiles

The mapping stack requires aggressive load balancing between the tethered devices.

| Model / Algorithm | Compute Target | Function | FPS / Rate | Latency | VRAM / RAM Footprint | CPU Load |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **FAST-LIO2 (IEKF)** | Orin NX (CPU) | Odometry & Deskewing | 50 Hz | 10 ms | 150 MB (RAM) | 2 Cores |
| **YOLOv11-pose** | Orin NX (GPU) | Pedestrian BBox / Skeleton | 30 Hz | 18 ms | 1.8 GB (Unified) | Low |
| **LV-DOT (Tracker)** | Orin NX (CPU) | Multi-Object Tracking | 30 Hz | <5 ms | 200 MB (RAM) | 1 Core |
| **Dynamic Masking** | Orin NX (CPU) | Masking dynamic points | 30 Hz | <2 ms | 50 MB (RAM) | 0.5 Core |
| **LCD-Splat / AG-SLAM** | RTX 5090 (GPU) | Global Static Mapping | 5 Hz | 150 ms | 6.5 GB (VRAM) | 3 Cores |
| **GPU Elevation Map** | RTX 5090 (GPU) | Footstep Terrain Grid | 20 Hz | 12 ms | 800 MB (VRAM) | 1 Core |

---

## 5. Hardware Integration & Deployment Analysis: Unitree G1

### Feasibility on Orin NX (16GB) + Tethered RTX 5090
Running heavy SLAM and VLM cognition natively on the Orin NX 16GB is physically impossible (an Orin cannot run Cosmos 3 Nano, LCD-Splat, and YOLOv11 simultaneously). However, our **Tethered Architecture** explicitly solves this:

1. **The Edge (Orin NX 16GB):** Exclusively handles the high-frequency, low-latency survival loops.
   - Total Memory Budget: `~2.2 GB / 16 GB` (FAST-LIO2, YOLO, LV-DOT).
   - This leaves 13.8 GB free for the base OS, ROS2 middleware, and the Unitree WBC locomotion stack.
   - By performing the Dynamic Masking locally on the Orin, we prevent saturating the Wi-Fi/Ethernet tether with useless dynamic point clouds.

2. **The Cloud/Backpack (RTX 5090 24GB Laptop):** Handles the asynchronous mapping and cognition.
   - Total Memory Budget: `6.5 GB (Splat) + 0.8 GB (Elevation) + 16.0 GB (Cosmos 3 Nano) = 23.3 GB / 24 GB`.
   - VRAM is tightly packed. This necessitates the **Context Mode Swapping** architecture designed previously: when the robot stops to interact (engaging Omni-LLM dialogue), it pages out the MPPI/Flow routing models, ensuring it never hits OOM crashes.

### End-to-End Recommended Stack Configuration
To target the required 20–30 Hz control loop for fluid humanoid navigation in dynamic environments:
1. **Sensors $\rightarrow$ Deskewing (Orin):** FAST-LIO2 operates at 50Hz.
2. **Dynamic Separation (Orin):** YOLOv11/LV-DOT operates at 30Hz to erase pedestrians.
3. **Map Construction (RTX 5090):** LCD-Splat operates asynchronously at 5Hz to avoid locking threads. GPU Elevation Mapping runs at 20Hz directly off the cleaned point cloud.
4. **Cognition & Routing (RTX 5090):** Cosmos VLM parses the Splat Maps and RGB feeds at 1Hz (Semantic Loop), providing goals to MPPI (running at 30Hz), which feeds into the Orin's WBC (running at 500Hz).
