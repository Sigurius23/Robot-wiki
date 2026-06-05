# Object-Centric Learning with Slot Attention

**Paper:** [arXiv:2006.15055](https://arxiv.org/abs/2006.15055)  
**Authors:** Francesco Locatello, Dirk Weissenborn, Thomas Unterthiner, et al. (Google Research)  
**Core Domain:** Object-Centric Representation, Scene Decomposition, Unsupervised Learning.

---

## 🔬 Core Contribution
Introduction of the **Slot Attention** module, an architectural component that decomposes a distributed feature map (e.g., from a CNN or ViT) into a set of task-dependent abstract representations called **slots**. Through a competitive iterative attention mechanism, each slot "binds" to a specific object or region in the input, enabling compositional scene understanding without explicit supervision.

## 🛠 Relevant Mechanisms for G1-JEPA
*   **Iterative Competitive Attention:** Slots compete for input "keys" via softmax normalized over the slots. This forces the model to partition the scene into discrete entities rather than learning a global "soup" of features.
*   **Compositional Generalization:** Because slots are exchangeable and object-centric, the G1 can generalize to new scenes by rearranging known "slots" (e.g., recognizing a "blue mat" in a new room).
*   **Decoupled Property Prediction:** Once bound to an object, each slot can be passed to downstream MLPs to predict specific properties like mass, friction, or $s_{nogo}$ status.

## 🔗 Interlinks to Project Components
- [x] **JEPA Predictor:** Instead of predicting the entire future latent state, the JEPA can predict the future of each **slot** independently, enabling "Object-Centric Imagination."
- [x] **Semantic Alignment (VL-JEPA):** We can align natural language commands to specific **slots** (e.g., "Avoid the object in Slot 3").
- [x] **Voxel Memory:** Slots can be used as the high-level semantic labels stored within the **4D Sparse Voxels**.

## 🚀 Actionable Integration Plan
1.  **Slot Encoder:** Implement a Slot Attention module after the Minkowski 4D Backbone to extract object-centric latents from the spatio-temporal volume.
2.  **Tracking:** Use the temporal consistency of MinkowskiNet to initialize slots across frames, ensuring the same slot ID tracks the same physical object.
3.  **Slot-Based MPPI:** Optimize action sequences by evaluating energy penalties per-slot (e.g., if Slot 2's predicted trajectory intersects the robot's heel voxel, apply penalty).
