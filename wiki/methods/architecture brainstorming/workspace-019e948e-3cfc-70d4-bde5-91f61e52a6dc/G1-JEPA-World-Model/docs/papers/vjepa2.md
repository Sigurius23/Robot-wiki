# V-JEPA 2: Self-Supervised Video Models Enable Understanding, Prediction and Planning

**Paper:** [arXiv:2506.09985](https://arxiv.org/abs/2506.09985)  
**Authors:** Mido Assran et al. (Meta AI)  
**Core Domain:** Self-Supervised World Models, Video Prediction, Robotic Planning.

---

## 🔬 Core Contribution
Introduction of **V-JEPA 2**, a world model trained on over 1 million hours of internet video. It demonstrates that massive passive observation (internet video) combined with minimal robotic interaction data (62 hours) can yield a model capable of high-fidelity physical reasoning, future state prediction, and zero-shot robotic planning.

## 🛠 Relevant Mechanisms for G1-JEPA
*   **Action-Conditioned Latent Prediction (V-JEPA 2-AC):** A variant fine-tuned on robot trajectories that predicts future video embeddings $\hat{s}_{y}$ conditioned on an action sequence $a_{1:T}$ and current state $s_k$.
*   **Teacher-Forcing and Rollout Objective:** The predictor is trained to match the encoder's latent state for the next frame (teacher-forcing) while also maintaining consistency over long-horizon autoregressive rollouts.
*   **Zero-Shot MPC Planning:** Enables the robot to reach a "Goal Image" by optimizing an action sequence in latent space using the Cross-Entropy Method (CEM) to minimize the distance between the predicted final state and the goal state: $E = \|P_\phi(a_{1:T}; s_k) - z_{goal}\|$.
*   **Spatiotemporal Masking:** The model learns features by predicting missing spatiotemporal patches, forcing it to understand both geometry (spatial) and dynamics (temporal).

## 🔗 Interlinks to Project Components
- [x] **JEPA Predictor:** V-JEPA 2-AC provides the foundational architecture for the G1's predictive loop, specifically the interaction between actions and latent state changes.
- [x] **Latent Planner:** The image-goal MPC logic directly aligns with our **Latent MPPI** strategy for reaching target visual states.
- [x] **Voxel Memory:** V-JEPA's spatiotemporal features can be projected into our **4D Sparse Voxels** to provide a rich temporal context.

## 🚀 Actionable Integration Plan
1.  **V-JEPA 2 Backbone:** Utilize the V-JEPA 2 ViT-g encoder as the primary "World Encoder" for the G1.
2.  **Action Integration:** Implement the V-JEPA 2-AC predictor head to handle the G1's joint-level action commands.
3.  **Goal-Conditioned MPPI:** Adapt the current `src/mppi_planner.py` to support "Image Goals" (e.g., a photo of a target object) by minimizing the latent distance to the goal embedding.
