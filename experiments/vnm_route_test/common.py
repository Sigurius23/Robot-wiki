"""Shared helpers for the offline GNM / ViNT / NoMaD route test.

The model-loading and image-transform code mirrors
robodhruv/visualnav-transformer (deployment/src/utils.py and navigate.py,
MIT license, Copyright (c) 2023 Dhruv Shah, Ajay Sridhar, Nitish Dashora,
Kyle Stachowicz, Kevin Black, Noriaki Hirose, Sergey Levine).
It is copied instead of imported because the upstream utils.py imports
ROS 1 (sensor_msgs) at module level, which we do not want to require.

torch and the upstream packages are imported lazily, so the numpy-only
dry-run model works on machines without a GPU or PyTorch.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Dict, List, Optional

import numpy as np
from PIL import Image

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")
MODEL_KINDS = ("gnm", "vint", "nomad")


# --------------------------------------------------------------------------
# Frame folders
# --------------------------------------------------------------------------

def _frame_key(name: str) -> int:
    digits = re.findall(r"\d+", os.path.splitext(name)[0])
    if not digits:
        raise ValueError(f"Frame file name has no number to sort by: {name}")
    return int(digits[-1])


def list_frames(folder: str) -> List[str]:
    """Image paths in a folder, sorted by the last number in each file name."""
    names = [n for n in os.listdir(folder) if n.lower().endswith(IMAGE_EXTENSIONS)]
    if not names:
        raise FileNotFoundError(f"No images found in {folder}")
    return [os.path.join(folder, n) for n in sorted(names, key=_frame_key)]


def load_images(paths: List[str]) -> List[Image.Image]:
    return [Image.open(p).convert("RGB") for p in paths]


def read_meta(folder: str) -> Dict:
    path = os.path.join(folder, "meta.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def write_json(path: str, data: Dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# --------------------------------------------------------------------------
# Model runners
# --------------------------------------------------------------------------

class StepResult:
    """Output of one localization + action step.

    dists:       predicted temporal distance to each candidate node
    next_offset: index (within the candidate window) that becomes the new
                 closest node, following upstream navigate.py
    traj:        chosen trajectory, shape (T, k); k = 2 (x, y) or 4 (x, y, cos, sin)
    samples:     NoMaD only, all sampled trajectories (S, T, 2)
    """

    def __init__(self, dists, next_offset, traj, samples=None):
        self.dists = np.asarray(dists, dtype=float).reshape(-1)
        self.next_offset = int(next_offset)
        self.traj = np.asarray(traj, dtype=float)
        self.samples = None if samples is None else np.asarray(samples, dtype=float)


class TorchVNM:
    """Runs a pretrained GNM, ViNT or NoMaD checkpoint exactly like navigate.py."""

    def __init__(self, config_path: str, ckpt_path: str, device: str = "cuda",
                 num_samples: int = 8, seed: int = 0):
        import torch
        import yaml

        self.torch = torch
        with open(config_path) as f:
            self.cfg = yaml.safe_load(f)
        self.kind = self.cfg["model_type"]
        if self.kind not in MODEL_KINDS:
            raise ValueError(f"Unsupported model_type {self.kind}")
        if device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA is not available. On an RTX 5090 you need a PyTorch build "
                "for CUDA 12.8 or newer.")
        self.device = torch.device(device)
        torch.manual_seed(seed)

        if self.device.type == "cuda":
            torch.cuda.reset_peak_memory_stats()
        self.model = _load_model(ckpt_path, self.cfg, self.device)
        self.model.eval()
        self.load_report = self.model.load_report
        self.weights_mb = self._allocated_mb()

        self.context_size = int(self.cfg["context_size"])
        self.image_size = list(self.cfg["image_size"])
        self.len_traj_pred = int(self.cfg["len_traj_pred"])
        self.normalize = bool(self.cfg.get("normalize", False))
        self.num_samples = num_samples

        if self.kind == "nomad":
            from diffusers.schedulers.scheduling_ddpm import DDPMScheduler
            from vint_train.training.train_utils import get_action

            self.get_action = get_action
            self.num_diffusion_iters = int(self.cfg["num_diffusion_iters"])
            self.noise_scheduler = DDPMScheduler(
                num_train_timesteps=self.num_diffusion_iters,
                beta_schedule="squaredcos_cap_v2",
                clip_sample=True,
                prediction_type="epsilon",
            )

    # -- memory / timing ---------------------------------------------------
    def _allocated_mb(self) -> Optional[float]:
        if self.device.type != "cuda":
            return None
        return self.torch.cuda.memory_allocated() / 2**20

    def peak_mb(self) -> Optional[float]:
        if self.device.type != "cuda":
            return None
        return self.torch.cuda.max_memory_allocated() / 2**20

    def sync(self) -> None:
        if self.device.type == "cuda":
            self.torch.cuda.synchronize()

    def gpu_name(self) -> Optional[str]:
        if self.device.type != "cuda":
            return None
        return self.torch.cuda.get_device_name(self.device)

    # -- inference ---------------------------------------------------------
    def _transform(self, imgs: List[Image.Image]):
        return _transform_images(imgs, self.image_size)

    def step(self, context: List[Image.Image], candidates: List[Image.Image],
             close_threshold: float) -> StepResult:
        torch = self.torch
        with torch.no_grad():
            obs = self._transform(context).to(self.device)            # [1, 3(c+1), H, W]
            goals = torch.cat([self._transform([g]) for g in candidates], dim=0).to(self.device)
            n = goals.shape[0]

            if self.kind in ("gnm", "vint"):
                dists, wps = self.model(obs.repeat(n, 1, 1, 1), goals)
                dists = dists.detach().cpu().numpy().reshape(-1)
                wps = wps.detach().cpu().numpy()                     # [n, T, k]
                m = int(np.argmin(dists))
                if dists[m] > close_threshold:
                    return StepResult(dists, m, wps[m])
                return StepResult(dists, m + 1, wps[min(m + 1, n - 1)])

            # NoMaD
            mask = torch.zeros(1).long().to(self.device)
            cond = self.model("vision_encoder", obs_img=obs.repeat(n, 1, 1, 1),
                              goal_img=goals, input_goal_mask=mask.repeat(n))
            dists = self.model("dist_pred_net", obsgoal_cond=cond)
            dists = dists.detach().cpu().numpy().reshape(-1)
            m = int(np.argmin(dists))
            sg_idx = min(m + int(dists[m] < close_threshold), n - 1)
            obs_cond = cond[sg_idx].unsqueeze(0)
            if obs_cond.dim() == 2:
                obs_cond = obs_cond.repeat(self.num_samples, 1)
            else:
                obs_cond = obs_cond.repeat(self.num_samples, 1, 1)
            naction = torch.randn((self.num_samples, self.len_traj_pred, 2), device=self.device)
            self.noise_scheduler.set_timesteps(self.num_diffusion_iters)
            for k in self.noise_scheduler.timesteps[:]:
                noise_pred = self.model("noise_pred_net", sample=naction, timestep=k,
                                        global_cond=obs_cond)
                naction = self.noise_scheduler.step(model_output=noise_pred, timestep=k,
                                                    sample=naction).prev_sample
            samples = self.get_action(naction).detach().cpu().numpy()  # [S, T, 2]
            # upstream: closest_node = start + min_idx (no +1 for NoMaD)
            return StepResult(dists, m, samples[0], samples)


class FakeVNM:
    """Numpy stand-in used for --dry-run. NOT a navigation model.

    Distance = scaled image difference between the newest context frame and
    each candidate node. Lateral waypoint offset steers away from the darker
    half of the image (the synthetic obstacle is dark). It exists only to
    exercise the pipeline end to end without a GPU.
    """

    def __init__(self, kind: str = "gnm", context_size: int = 5, len_traj_pred: int = 5):
        self.kind = kind
        self.cfg = {"model_type": kind, "normalize": True, "context_size": context_size}
        self.context_size = context_size
        self.len_traj_pred = len_traj_pred
        self.normalize = True
        self.weights_mb = None
        self.load_report = {"note": "dry-run stand-in, no weights loaded"}

    @staticmethod
    def _small(img: Image.Image) -> np.ndarray:
        return np.asarray(img.convert("L").resize((32, 24)), dtype=float) / 255.0

    def step(self, context, candidates, close_threshold) -> StepResult:
        cur = self._small(context[-1])
        dists = np.array([np.clip(np.abs(cur - self._small(c)).mean() * 80.0, 0, 20)
                          for c in candidates])
        left, right = cur[:, :16].mean(), cur[:, 16:].mean()
        lateral = float(np.clip((left - right) * 4.0, -1, 1))   # dark left -> steer right (y < 0)
        t = np.arange(1, self.len_traj_pred + 1, dtype=float)
        traj = np.stack([t, lateral * t / self.len_traj_pred], axis=1)
        m = int(np.argmin(dists))
        if dists[m] > close_threshold:
            return StepResult(dists, m, traj)
        return StepResult(dists, m + 1, traj)

    def peak_mb(self):
        return None

    def sync(self):
        pass

    def gpu_name(self):
        return None


# --------------------------------------------------------------------------
# Copies of upstream helpers (see module docstring for license)
# --------------------------------------------------------------------------

def _transform_images(pil_imgs: List[Image.Image], image_size: List[int]):
    """Upstream transform_images() with center_crop=False (navigate.py default)."""
    import torch
    from torchvision import transforms

    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    out = []
    for img in pil_imgs:
        img = img.resize(tuple(image_size))  # image_size is [width, height]
        out.append(torch.unsqueeze(transform(img), 0))
    return torch.cat(out, dim=1)


def _load_model(model_path: str, config: Dict, device):
    """Upstream load_model()."""
    import torch

    model_type = config["model_type"]
    if model_type == "gnm":
        from vint_train.models.gnm.gnm import GNM
        model = GNM(config["context_size"], config["len_traj_pred"], config["learn_angle"],
                    config["obs_encoding_size"], config["goal_encoding_size"])
    elif model_type == "vint":
        from vint_train.models.vint.vint import ViNT
        model = ViNT(
            context_size=config["context_size"],
            len_traj_pred=config["len_traj_pred"],
            learn_angle=config["learn_angle"],
            obs_encoder=config["obs_encoder"],
            obs_encoding_size=config["obs_encoding_size"],
            late_fusion=config["late_fusion"],
            mha_num_attention_heads=config["mha_num_attention_heads"],
            mha_num_attention_layers=config["mha_num_attention_layers"],
            mha_ff_dim_factor=config["mha_ff_dim_factor"],
        )
    elif model_type == "nomad":
        from diffusion_policy.model.diffusion.conditional_unet1d import ConditionalUnet1D
        from vint_train.models.nomad.nomad import DenseNetwork, NoMaD
        from vint_train.models.nomad.nomad_vint import NoMaD_ViNT, replace_bn_with_gn

        if config["vision_encoder"] == "nomad_vint":
            vision_encoder = NoMaD_ViNT(
                obs_encoding_size=config["encoding_size"],
                context_size=config["context_size"],
                mha_num_attention_heads=config["mha_num_attention_heads"],
                mha_num_attention_layers=config["mha_num_attention_layers"],
                mha_ff_dim_factor=config["mha_ff_dim_factor"],
            )
        elif config["vision_encoder"] == "vit":
            from vint_train.models.vint.vit import ViT
            vision_encoder = ViT(
                obs_encoding_size=config["encoding_size"],
                context_size=config["context_size"],
                image_size=config["image_size"],
                patch_size=config["patch_size"],
                mha_num_attention_heads=config["mha_num_attention_heads"],
                mha_num_attention_layers=config["mha_num_attention_layers"],
            )
        else:
            raise ValueError(f"Vision encoder {config['vision_encoder']} not supported")
        vision_encoder = replace_bn_with_gn(vision_encoder)
        noise_pred_net = ConditionalUnet1D(
            input_dim=2,
            global_cond_dim=config["encoding_size"],
            down_dims=config["down_dims"],
            cond_predict_scale=config["cond_predict_scale"],
        )
        model = NoMaD(vision_encoder=vision_encoder, noise_pred_net=noise_pred_net,
                      dist_pred_net=DenseNetwork(embedding_dim=config["encoding_size"]))
    else:
        raise ValueError(f"Invalid model type: {model_type}")

    # weights_only=False: the GNM/ViNT checkpoints store a pickled model object.
    # Only load checkpoints downloaded from the official link in the README.
    try:
        checkpoint = torch.load(model_path, map_location=device, weights_only=False)
    except TypeError:  # older PyTorch without the weights_only argument
        checkpoint = torch.load(model_path, map_location=device)
    if model_type == "nomad":
        state_dict = checkpoint
    else:
        loaded = checkpoint["model"]
        try:
            state_dict = loaded.module.state_dict()
        except AttributeError:
            state_dict = loaded.state_dict()
    # strict=False as upstream, but keep the mismatch so a bad load is visible
    result = model.load_state_dict(state_dict, strict=False)
    model.load_report = {
        "missing_keys": len(result.missing_keys),
        "unexpected_keys": len(result.unexpected_keys),
        "missing_examples": list(result.missing_keys)[:5],
        "unexpected_examples": list(result.unexpected_keys)[:5],
    }
    model.to(device)
    return model


def now() -> float:
    return time.perf_counter()
