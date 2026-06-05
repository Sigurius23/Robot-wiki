# WorldRFT: Latent World Model Planning with Reinforcement Fine-Tuning for Autonomous Driving

**Paper:** [arXiv:2512.19133](https://arxiv.org/abs/2512.19133)  
**Authors:** Pengxuan Yang et al. (Institute of Automation, CAS; Li Auto)  
**Core Domain:** Reinforcement Learning Fine-Tuning (RFT), Planning-Oriented Latent Models.

---

## 🔬 Core Contribution
Introduction of **WorldRFT**, a framework that shifts latent world models from purely reconstruction-oriented learning (predicting pixels/features) to **planning-oriented** learning. It uses Reinforcement Fine-Tuning (RFT) to align latent representations with safety-critical driving objectives, drastically reducing collision rates.

## 🛠 Relevant Mechanisms for G1-JEPA
*   **Hierarchical Planning Refinement (HPR):** Decomposes the G1's high-level goal into three manageable latent sub-tasks:
    1.  **Target Region Localization:** Deciding where the feet should land globally.
    2.  **Spatial Path Planning:** Identifying the geometric route.
    3.  **Temporal Trajectory Prediction:** Executing the gait timing.
*   **Group Relative Policy Optimization (GRPO):** A reinforcement learning technique used to fine-tune the JEPA policy. It compares groups of generated trajectories and rewards the ones that are collision-free.
*   **Collision-Aware Rewards:** Explicitly penalizes latent trajectories that intersect with "No-Go" zones or obstacles. This is the training-time counterpart to our inference-time **Energy-Based Constraints (EBC)**.
*   **Spatial-aware World Encoder (SWE):** Uses a vision-geometry backbone to ensure the latent features aren't just semantic, but preserve the metric 3D structure needed for balance.

## 🔗 Interlinks to Project Components
- [x] **Latent Planner:** Directly provides the "Hierarchical Refinement" logic for our MPPI planner.
- [ ] **JEPA Predictor:** Suggests that the predictor should be fine-tuned via RL, not just supervised learning, to understand "Safety Principles."
- [x] **Safety Layer:** The "Collision-Aware Reward" logic informs how we define the $s_{nogo}$ penalty thresholds.

## 🚀 Actionable Integration Plan
1.  **HPR Implementation:** Modify `src/mppi_planner.py` to use a hierarchical structure (Locate -> Path -> Time).
2.  **RFT Post-Training:** Design a "Safety Fine-Tuning" phase for the G1 where it explores latent trajectories in simulation and is penalized for "hallucinated collisions."
3.  **GRPO Adaptation:** Use the Group Relative logic to refine the MPPI sampling distribution, making it more robust to safety-critical edge cases.
