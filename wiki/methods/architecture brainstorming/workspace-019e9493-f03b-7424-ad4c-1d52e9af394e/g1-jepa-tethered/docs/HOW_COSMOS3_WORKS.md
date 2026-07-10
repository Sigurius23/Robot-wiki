# How Cosmos 3 Works & How We'd Run It

**Updated:** June 9, 2026
**Sources:** [NVIDIA Cosmos GitHub](https://github.com/nvidia/Cosmos), [Hugging Face Blog](https://huggingface.co/blog/nvidia/cosmos-3-for-physical-ai), [Technical Blog](https://developer.nvidia.com/blog/develop-physical-ai-reasoning-world-and-action-models-with-nvidia-cosmos-3/)

---

## 1. Architecture: How It Actually Works

### The Two-Tower Design

Cosmos 3 is a **Mixture-of-Transformers (MoT)** — a single model with two interacting "towers" that share parameters:

```
                    ┌─────────────────────────┐
  Text/Image/Video ─┤   Dedicated Encoders    ├──→ Shared Representation Space
  Action ───────────┤  (ViT, VAE, Action Vec) │
                    └───────────┬─────────────┘
                                │
              ┌─────────────────▼─────────────────┐
              │     Mixture-of-Transformers        │
              │                                    │
              │  ┌──────────┐    ┌──────────────┐ │
              │  │ AR Tower │←──→│  DM Tower    │ │
              │  │(Reasoner)│Joint│ (Generator)  │ │
              │  │Causal    │Attn│ Diffusion    │ │
              │  │Attention │    │ Denoising    │ │
              │  └────┬─────┘    └──────┬───────┘ │
              │       │                  │         │
              └───────┼──────────────────┼─────────┘
                      │                  │
                      ▼                  ▼
                   Text              Image/Video
              (reasoning,          (future frames,
               captions,           action sequences,
               planning)           sound)
```

### How the Towers Interact

- **AR (Reasoner) Tower**: Autoregressive transformer using **causal self-attention**. Processes vision + text inputs and predicts next tokens. This is the "brain" that understands the scene. Think Qwen3-VL-style VLM.
- **DM (Generator) Tower**: Diffusion transformer using **full attention**. Takes noisy tokens and iteratively denoises them into coherent images, videos, audio, or action sequences.
- **Joint Attention**: Both towers use the same transformer layers but with separate parameter sets. They communicate through **joint attention layers** where AR tokens attend to DM tokens and vice versa. This is the key innovation — a single forward pass can do both reasoning AND generation.
- **Unified mRoPE**: A 3D multi-dimensional rotary position embedding encodes spatial AND temporal structure across all modalities. This is how it understands that a video has both spatial frames AND temporal ordering.

### The Two Runtime Surfaces

| Surface | What it does | Inputs | Outputs |
|:---|:---|:---|:---|
| **Reasoner** | Understand & reason | Text, images, video | Text (captions, plans, answers) |
| **Generator** | Generate & predict | Text, images, video, action | Images, video, sound, action |

The Generator always activates both towers (Reasoner does the understanding, Generator does the creating). The Reasoner can be called standalone for cheaper inference.

---

## 2. Modality Matrix: What Goes In, What Comes Out

This is the full I/O table from the GitHub:

| Workflow | Input | Output | What It Means For Us |
|:---|:---|:---|:---|
| **Text-to-Video** | Text prompt | Video | Generate training scenarios |
| **Image-to-Video** | Image + text | Video | "Given this camera view, predict what happens next" |
| **Video-to-Video** | Source video + text | Transformed video | Modify a recorded trajectory |
| **Forward Dynamics** | Image + action chunk | Predicted video | **"If I execute these joint commands, what will I see?"** |
| **Inverse Dynamics** | Video + instruction | Predicted action | **"What actions produced this observed motion?"** |
| **Policy** | Image + instruction | Video + action chunk | **"Given this scene and task, what should I do?"** |
| **Caption** | Video | Text description | Scene understanding |
| **Embodied Reasoning** | Video + question | Text answer | "What should the robot do next?" |
| **Action Chain-of-Thought** | Image/video + prompt | Text/JSON trajectory | Step-by-step action reasoning |

### Action Modalities Supported (This Is Critical)

Cosmos 3 natively supports action dimensions for different embodiments:

| Embodiment | Action Dims | What |
|:---|:---|:---|
| Camera motion | 9D | Pose changes |
| Autonomous vehicle | 9D | Steering, throttle, brake |
| Egocentric motion | 57D | Full body + head tracking |
| Single-arm robot | 10D | DROID, UR, Franka, Bridge, UMI formats |
| Dual-arm robot | 20D | Dual DROID arms |
| **Humanoid robot** | **29D** | **AgiBot format** |

**This is huge for us.** Cosmos 3 has a pre-built action head for humanoid robots (29 DoF in AgiBot format). The Unitree G1 has 43 DoF — we'd need to adapt (remap the action space or post-train), but the architecture supports it.

---

## 3. How We Would Run It: Three Paths

### Path A: Diffusers (Research/Development)

Best for: Experimentation, prototyping, custom pipelines.

```python
import torch
from diffusers import Cosmos3OmniPipeline

# Load Cosmos 3 Nano (16B) on RTX 5090
pipe = Cosmos3OmniPipeline.from_pretrained(
    "nvidia/Cosmos3-Nano",
    torch_dtype=torch.bfloat16,  # 16GB VRAM baseline
    device_map="cuda",
)

# === SCENE UNDERSTANDING (Reasoner mode) ===
# Show Cosmos 3 what the G1 sees, ask it what's happening
result = pipe(
    prompt="What objects are on the table and where are they relative to the robot?",
    image="g1_camera_view.jpg",  # From RealSense D435i
    # Returns text: "There is a blue cup 30cm to the left..."
)

# === FUTURE PREDICTION (Generator, Forward Dynamics) ===
# "If the G1 steps forward with these joint angles, what will the world look like?"
result = pipe(
    prompt="",
    image="g1_current_view.jpg",
    action=[0.1, -0.05, ...],  # 29D humanoid action vector
    num_frames=30,             # 1 second at 30fps
)
# Returns: predicted video frames + optionally action sequence

# === POLICY GENERATION (Generator, Policy mode) ===
# "Go pick up the red cup"
result = pipe(
    prompt="Pick up the red cup on the table",
    image="g1_camera_view.jpg",
    num_frames=60,             # 2 seconds at 30fps
)
# Returns: video of predicted execution + action trajectory
export_to_video(result.video, "planned_trajectory.mp4")
```

**VRAM Reality Check for RTX 5090 (24GB):**
- **BF16**: Needs ~32GB for full 16B model → won't fit without offloading
- **FP8 quantized**: ~16GB → fits with some headroom
- **NVFP4 quantized**: ~8GB → comfortable fit, 2× speedup
- **With CPU offloading** (`device_map="auto"`): fits but slower

**Inference time** (estimate based on diffusion models at this scale):
- Text-to-video (189 frames, 35 steps): 30–120 seconds depending on quantization
- Single-frame reasoning: 1–5 seconds
- Action policy generation: 10–60 seconds

**This is NOT real-time for the 40Hz control loop.** Cosmos 3 operates at the Semantic loop level (0.1–1 Hz). It provides high-level goals, not motor commands.

### Path B: vLLM-Omni (Production/Low-Latency)

Best for: Deploying as a service, OpenAI-compatible API, faster inference.

```bash
# One-time setup: pull and run as a server
docker run --runtime nvidia --gpus all \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -v "$(pwd):/workspace" \
  -p 8000:8000 \
  --ipc=host \
  vllm/vllm-omni:cosmos3 \
  vllm serve nvidia/Cosmos3-Nano \
    --omni \
    --model-class-name Cosmos3OmniDiffusersPipeline \
    --allowed-local-media-path / \
    --port 8000 \
    --init-timeout 1800
```

Then query it from our control code:

```python
import requests

# === TEXT-TO-VIDEO (generate training scenarios) ===
response = requests.post("http://localhost:8000/v1/videos/sync", files={
    "prompt": (None, "A Unitree G1 humanoid walks through a cluttered lab and picks up a tool from the workbench."),
    "size": (None, "1280x720"),
    "num_frames": (None, "189"),
    "fps": (None, "24"),
    "num_inference_steps": (None, "35"),
})

# === POLICY: Generate actions for the G1 ===
response = requests.post("http://localhost:8000/v1/videos", files={
    "prompt": (None, "Pick up the red cup on the table"),
    "input_reference": open("g1_camera.jpg", "rb"),
    "extra_params": (None, json.dumps({
        "action_mode": "policy",
        "domain_name": "agibot_humanoid",  # 29D humanoid action space
        "raw_action_dim": 29,
        "action_chunk_size": 50
    }))
})
# Returns: video + action chunk (29D × 50 timesteps)
```

### Path C: NIM Microservice (Easiest Deployment)

Best for: Production, optimized inference, automatic quantization.

```bash
docker run --gpus=all \
  -e NGC_API_KEY=$NGC_API_KEY \
  -e NIM_MODEL_SIZE=nano \
  -p 8000:8000 \
  nvcr.io/nim/nvidia/cosmos3-reasoner:latest
```

Comes with automatic NVFP4 quantization, continuous batching, and EVS (Efficient Video Sampling). This is probably the best path for us once we move beyond experimentation.

---

## 4. What Cosmos 3 Would Actually DO For Our Pipeline

### Replace These Components

| Current Component | Replaced By | How |
|:---|:---|:---|
| **DINOv3** (unsupervised segmentation) | Cosmos 3 Reasoner | Native visual understanding, object grounding via 2D grounding mode |
| **Slot Attention** (object-centric decomposition) | Cosmos 3 Reasoner | Object-level reasoning with "Describe Anything" mode |
| **VL-JEPA** (vision-language grounding) | Cosmos 3 Reasoner | Built-in text-to-scene understanding |
| **V-JEPA 2** (video prediction) | Cosmos 3 Generator (Forward Dynamics) | Action-conditioned world simulation |
| **MPPI Planner** (trajectory sampling) | Cosmos 3 Generator (Policy mode) | Direct action trajectory generation from prompts |

### Keep These Components

| Component | Why We Keep It |
|:---|:---|
| **4D Voxel Latent Memory** | Cosmos 3 has no persistent spatial memory — no object permanence for blind spots |
| **FAST-LIO2 Odometry** | Cosmos 3 doesn't do real-time state estimation |
| **WBC Controller** (500 Hz) | Cosmos 3 inference is 100–1000× too slow for motor control |
| **CBF Safety Filter** | Physics-level safety is a separate concern from world modeling |
| **Tether Safety** (yaw penalty, link-loss buffer) | Our unique hardware constraint |
| **Acoustic-JEPA** | Cosmos 3 supports audio generation, not hazard detection from audio |

### The New Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ RTX 5090 (Offboard)                                              │
│                                                                  │
│  Cosmos 3 Nano (vLLM-Omni server, NVFP4)                        │
│  ┌────────────────────────────────────────────────┐             │
│  │ REASONER (text queries, 0.1–1 Hz)               │             │
│  │  "Is the path to the kitchen clear?"            │             │
│  │  "What objects are on the workbench?"           │ → text     │
│  │  "Where is the red cup relative to the robot?" │             │
│  └────────────────────────────────────────────────┘             │
│  ┌────────────────────────────────────────────────┐             │
│  │ GENERATOR - Policy (task → actions, 0.1–0.5 Hz)│             │
│  │  "Pick up the red cup"                         │             │
│  │  → predicted video + 29D action chunk × 50     │ → actions  │
│  └────────────────────────────────────────────────┘             │
│                         │                                       │
│          ┌──────────────▼──────────────┐                        │
│          │ 4D Voxel Latent Memory      │                        │
│          │ • Persists Cosmos 3 outputs │                        │
│          │ • Rearward blind spot check │  10–40 Hz               │
│          │ • Uncertainty-triggered     │                        │
│          │   damping                   │                        │
│          └──────────────┬──────────────┘                        │
│                         │ refined trajectory                    │
│          ┌──────────────▼──────────────┐                        │
│          │ Trajectory Interpolator     │  40 Hz                  │
│          │ • Smoothes Cosmos 3 actions │                        │
│          │ • Tether yaw penalty        │                        │
│          │ • Remaps 29D → 43D G1 DoF  │                        │
│          └──────────────┬──────────────┘                        │
└─────────────────────────┼──────────────────────────────────────┘
                          │ G1 joint targets @ 40Hz
┌─────────────────────────▼──────────────────────────────────────┐
│ Jetson Orin NX (Onboard)                                        │
│  ┌──────────────────────────────────────────┐                  │
│  │ Whole-Body Controller (WBC) @ 500 Hz     │                  │
│  │  • IK/ID solving                         │                  │
│  │  • CBF safety filter                      │                  │
│  │  • Link-loss trajectory buffer            │                  │
│  │  • FAST-LIO2 state estimation             │                  │
│  └──────────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. The Action Space Challenge: 29D AgiBot → 43D G1

This is our main integration challenge. Cosmos 3 outputs actions in **29D AgiBot humanoid format**. The G1 has 43 DoF. Options:

### Option A: Post-Train Cosmos 3 on G1 Data
- Collect G1 teleoperation data (joint angles + camera feeds)
- Use Cosmos 3's open post-training scripts to fine-tune the action head
- Maps directly: camera → 43D G1 joints
- **Best quality, most work.** Requires substantial G1 demonstration data.

### Option B: Remap in the Trajectory Interpolator
- Cosmos 3 outputs 29D → we map to 43D via a learned mapping
- Train a small MLP: 29D → 43D using kinematic constraints
- **Faster to implement, lower quality.** The G1 has different kinematics than AgiBot.

### Option C: Dimensionality Reduction then Expansion
- Cosmos 3 outputs 29D → project to a shared "task space" (end-effector poses, CoM target) → G1 IK solver computes 43D
- **Most robust.** Task-space control is embodiment-agnostic. The WBC handles the mapping.

**Recommendation:** Start with Option C for rapid prototyping. The task space (6D end-effector + 3D CoM + 3D torso orientation = 12D) is well within what Cosmos 3 can learn from 29D actions. Collect G1 teleoperation data for Option A in parallel.

---

## 6. Getting Started: Step-by-Step

### Step 1: Check VRAM Feasibility
```bash
# Check CUDA version
nvidia-smi
# Need: CUDA 12.8+ for Blackwell (RTX 5090)

# Check VRAM
nvidia-smi --query-gpu=memory.total --format=csv
# Need: 24GB available
```

### Step 2: Install Diffusers Path (Quickest Start)
```bash
uv venv --python 3.13 --seed --managed-python
source .venv/bin/activate
uv pip install --torch-backend=auto \
  "diffusers @ git+https://github.com/huggingface/diffusers.git" \
  accelerate torch torchvision transformers \
  imageio imageio-ffmpeg huggingface_hub av

# Authenticate with Hugging Face
huggingface-cli login
```

### Step 3: Test Scene Understanding (Reasoner)
```python
import torch
from diffusers import Cosmos3OmniPipeline

pipe = Cosmos3OmniPipeline.from_pretrained(
    "nvidia/Cosmos3-Nano",
    torch_dtype=torch.bfloat16,
    device_map="auto",  # Auto offload if OOM
)
# Test with a robotics scene
result = pipe(
    prompt="A table with a red cup, a blue plate, and a silver fork.",
    num_frames=1, height=720, width=1280,
)
result.video[0].save("test_scene.jpg")
```

### Step 4: Test Action Generation
```python
# Policy mode: "What should the robot do?"
result = pipe(
    prompt="Pick up the red cup and place it on the blue plate.",
    image="test_scene.jpg",
    # In Diffusers, action modes are coming — for now, use vLLM-Omni
)
```

### Step 5: Switch to vLLM-Omni for Action Workflows
```bash
docker run --runtime nvidia --gpus all \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -p 8000:8000 --ipc=host \
  vllm/vllm-omni:cosmos3 \
  vllm serve nvidia/Cosmos3-Nano \
    --omni \
    --model-class-name Cosmos3OmniDiffusersPipeline \
    --port 8000 --init-timeout 1800
```

Then test action generation:
```bash
curl -X POST http://localhost:8000/v1/videos \
  -F "prompt=Pick up the red cup" \
  -F "input_reference=@test_scene.jpg" \
  -F 'extra_params={"action_mode":"policy","domain_name":"agibot_humanoid","raw_action_dim":29,"action_chunk_size":50}'
```

---

## 7. Latency Budget & Hardware Fit

| Mode | Hardware | Quantization | Est. Latency | Use |
|:---|:---|:---|:---|:---|
| Reasoner (single frame) | RTX 5090 | FP8 | 1–3s | Scene Q&A |
| Reasoner (video, 5s) | RTX 5090 | FP8 | 5–15s | Situation understanding |
| Generator (T2V, 189fr) | RTX 5090 | NVFP4 | 30–90s | Training data gen |
| Generator (policy) | RTX 5090 | NVFP4 | 10–30s | Action planning |
| Generator (policy) | H100 | BF16 | 2–5s | Production |
| Reasoner (NIM) | RTX 5090 | NVFP4 | 0.5–2s | Fast scene Q&A |

**Bottom line:** Cosmos 3 runs on the RTX 5090 at ~0.5–2 Hz for reasoning, ~0.03–0.1 Hz for full video generation. This is perfect for the Semantic loop. It cannot replace the 40Hz Predictive loop or the 500Hz Reactive loop.

---

## 8. Key Limitations

1. **No persistent memory**: Every Cosmos 3 call is stateless. It processes what you give it and returns a result. Our 4D Voxel Memory fills this gap.
2. **No real-time control**: 1–30 second latency. Not suitable for the 40Hz or 500Hz loops.
3. **29D humanoid action space**: Needs adaptation for the G1's 43 DoF.
4. **Action mode still maturing**: In vLLM-Omni, action support (policy/forward-dynamics) is still in code review. Text/image/video modes are fully merged.
5. **Linux only**: The pipeline requires Linux. Our RTX 5090 laptop presumably runs Linux.
6. **First-run download**: Cosmos3-Nano is ~32GB of weights. Cache it on the NVMe SSD.

---

## 9. What This Means Architecturally

Cosmos 3 doesn't replace our architecture — it **collapses our Semantic loop into a single, more capable model** while validating that our three-loop split is correct:

| Loop | Before Cosmos 3 | After Cosmos 3 |
|:---|:---|:---|
| **Semantic** (0.1–1 Hz) | DINO + Slot Attention + VL-JEPA | **Cosmos 3 Reasoner + Generator** |
| **Predictive** (5–40 Hz) | V-JEPA 2 + MPPI | V-JEPA 2 + MPPI **or** distilled Cosmos student |
| **Reactive** (500 Hz) | CBF + FAST-LIO2 + WBC | CBF + FAST-LIO2 + WBC *(unchanged)* |

And our unique components — 4D Voxel Memory, tether safety, acoustic hazard detection — remain as differentiators that no foundation model provides.
