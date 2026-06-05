Transitioning the Unitree G1 from traditional SLAM to a mapless Joint Embedding Predictive Architecture (JEPA) requires shifting from Cartesian coordinate grids to abstract, continuous latent spaces. Here is how spatial constraints and rearward navigation are operationalized given the G1’s specific hardware limits—such as the NVIDIA Jetson Orin NX compute envelope and the severe vertical blind spots of its sensors.

**Defining "No-Go" Zones in Latent Space**

In a mapless JEPA system, you cannot define an exclusion zone by injecting an infinite-cost heuristic into a geometric grid. Instead, the G1 must enforce spatial constraints using a blend of semantic grounding and energy-based penalties directly within the embedding space:

- **Semantic Alignment via VL-JEPA:** The operator inputs constraints via natural language or an audio command processed by the G1's 4-microphone array (e.g., "Do not step on the blue mat"). A distilled Vision-Language JEPA—optimized for the Orin NX via TensorRT—converts this textual constraint into a target latent embedding, mathematically denoted as $s_{nogo}$.
- **Energy-Based Constraints (EBC):** To enforce this rule dynamically, a Model Predictive Path Integral (MPPI) controller generates candidate action sequences, $Z = \{z_1, z_2, ... z_N\}$, over the latent space. For each action, the JEPA network forecasts a future predicted embedding, $\hat{s}_y$.
- **Trajectory Pruning:** The system computes the cosine similarity between the predicted state $\hat{s}_y$ and the constraint embedding $s_{nogo}$. If the similarity crosses a threshold, the system applies an infinite energy penalty to that specific trajectory, instantly pruning it during the latent tree search and preventing the robot from visualizing or executing the action.
- **Latent Safety Filters:** To manage out-of-distribution hazards, Hamilton-Jacobi reachability analysis is applied to map out a "Latent Failure Set". If the robot's predicted trajectory intersects with the backward reachable tube of a known failure state, a safety-preserving recovery action overrides the nominal navigation policy.

**Rearward Navigation and Blind Collision Avoidance**

The G1 relies on a top-mounted LIVOX-MID360 LiDAR, which provides 360° horizontal coverage but only a 59° vertical field of view. Consequently, the immediate floor area extending outward from the robot's heels is completely invisible. Relying purely on standard generative models to step backward is extremely dangerous due to "Stability Decay"—a flaw where autoregressive models "forget" unobserved regions after a short temporal horizon.

To navigate this safely, the state-of-the-art methodology dictates a **Hierarchical World Model (H-WM)** that fuses 4D memory with low-level physical reactivity:

- **4D Sparse Voxel Latent Memory:** Instead of a flat feature vector, the latent space is structurally formatted as a 3D sparse voxel grid in the Orin NX's RAM. As the G1 walks forward, it populates this grid with semantic embeddings. When the robot initiates a backward step, it explicitly queries the voxels located behind it, achieving object permanence for the space it just observed.
- **Uncertainty-Triggered Damping:** If the memory in a rearward voxel is missing or has decayed, the model's epistemic uncertainty spikes. The latent safety filter uses this uncertainty threshold to preemptively trigger a speed reduction or a safe halting procedure (similar to the G1's L1+A damping mode), strictly refusing to allow a blind step into the unknown.
- **Proprioceptive-Inertial Fallback (CBF):** Latent memory cannot track dynamic obstacles (e.g., a human silently walking behind the robot). Therefore, high-frequency (500 Hz+) Control Barrier Functions (CBFs) operate directly on the G1’s IMU and dual joint encoders as an absolute fail-safe. If the robot steps backward and its heel encounters unexpected resistance or a lack of support, this low-level controller instantly bypasses the world model to shift momentum and prevent a fall.

[... Full Technical Analysis Included in Repository ...]
