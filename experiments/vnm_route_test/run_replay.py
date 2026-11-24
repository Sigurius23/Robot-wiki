"""Replay a recorded test walk through GNM, ViNT and/or NoMaD, open loop.

For every frame of the test walk this does what upstream navigate.py does
on the robot: localize against a window of topomap nodes, pick a subgoal,
and predict waypoints. Nothing is sent to a robot. Results go to
<out>/<model>.jsonl (one line per step) and <out>/<model>.meta.json.

Examples (on the RTX 5090 laptop, from this folder):
  python run_replay.py --topomap data/topomap --test data/test_obstacle \
      --vnm-repo ~/visualnav-transformer --models gnm vint nomad --out results/test_obstacle

  # pipeline check without GPU or weights:
  python run_replay.py --topomap data/topomap --test data/test_obstacle --dry-run \
      --models gnm vint nomad --out results/dry
"""

import argparse
import json
import os
import platform

import numpy as np

from common import FakeVNM, TorchVNM, list_frames, load_images, now, read_meta, write_json

# upstream deployment/config/models.yaml: model name -> (train config, checkpoint file)
UPSTREAM_MODELS = {
    "gnm": ("train/config/gnm.yaml", "deployment/model_weights/gnm_large.pth"),
    "vint": ("train/config/vint.yaml", "deployment/model_weights/vint.pth"),
    "nomad": ("train/config/nomad.yaml", "deployment/model_weights/nomad.pth"),
}


def build_runner(name, args):
    if args.dry_run:
        ctx = 3 if name == "nomad" else 5
        return FakeVNM(kind=name, context_size=ctx, len_traj_pred=8 if name == "nomad" else 5)
    if not args.vnm_repo:
        raise SystemExit("--vnm-repo is required unless --dry-run is set")
    cfg_rel, ckpt_rel = UPSTREAM_MODELS[name]
    cfg = os.path.join(os.path.expanduser(args.vnm_repo), cfg_rel)
    ckpt = os.path.join(os.path.expanduser(args.vnm_repo), ckpt_rel)
    if not os.path.exists(ckpt):
        raise SystemExit(f"Checkpoint not found: {ckpt} (see README, step 3)")
    return TorchVNM(cfg, ckpt, device=args.device, num_samples=args.num_samples, seed=args.seed)


def replay(name, runner, topomap, test_frames, args):
    goal_node = len(topomap) - 1 if args.goal_node == -1 else args.goal_node
    closest = 0
    ctx_len = runner.context_size + 1
    scale = (args.max_v / args.rate) if runner.normalize else 1.0
    rows = []

    for i in range(len(test_frames)):
        if i + 1 < ctx_len:
            continue  # upstream waits until the context queue is full
        context = test_frames[i + 1 - ctx_len: i + 1]
        start = max(closest - args.radius, 0)
        end = min(closest + args.radius + 1, goal_node)
        candidates = topomap[start:end + 1]

        runner.sync()
        t0 = now()
        res = runner.step(context, candidates, args.close_threshold)
        runner.sync()
        ms = (now() - t0) * 1000.0

        closest = min(start + res.next_offset, goal_node)
        wp = res.traj[min(args.waypoint, len(res.traj) - 1)]
        row = {
            "frame": i,
            "window": [start, start + len(candidates) - 1],
            "closest_node": int(closest),
            "min_dist": float(res.dists.min()),
            "dists": [round(float(d), 3) for d in res.dists],
            "waypoint_norm": [float(v) for v in wp[:2]],
            "waypoint_m": [float(v) * scale for v in wp[:2]],
            "traj_norm": np.round(res.traj[:, :2], 4).tolist(),
            "reached_goal": bool(closest == goal_node),
            "ms": round(ms, 3),
        }
        if res.samples is not None:
            ys = res.samples[:, min(args.waypoint, res.samples.shape[1] - 1), 1]
            row["sample_lateral_spread"] = float(ys.max() - ys.min())
        rows.append(row)
    return rows, goal_node


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--topomap", required=True)
    p.add_argument("--test", required=True, help="frames of the test walk (extract_frames.py output)")
    p.add_argument("--out", required=True)
    p.add_argument("--models", nargs="+", default=["gnm", "vint", "nomad"], choices=list(UPSTREAM_MODELS))
    p.add_argument("--vnm-repo", help="path to a clone of robodhruv/visualnav-transformer")
    p.add_argument("--device", default="cuda")
    p.add_argument("--dry-run", action="store_true", help="numpy stand-in model, no torch needed")
    # navigate.py defaults
    p.add_argument("--radius", type=int, default=4)
    p.add_argument("--close-threshold", type=float, default=3)
    p.add_argument("--waypoint", type=int, default=2)
    p.add_argument("--goal-node", type=int, default=-1)
    p.add_argument("--num-samples", type=int, default=8)
    p.add_argument("--seed", type=int, default=0)
    # metric scaling, like upstream robot.yaml (max_v, frame_rate)
    p.add_argument("--max-v", type=float, default=0.5, help="m/s used to scale normalized waypoints")
    p.add_argument("--rate", type=float, default=None, help="control rate in Hz (default: test fps)")
    args = p.parse_args()

    test_meta = read_meta(args.test)
    if args.rate is None:
        args.rate = float(test_meta.get("fps", 4.0))
    os.makedirs(args.out, exist_ok=True)

    topomap = load_images(list_frames(args.topomap))
    test_frames = load_images(list_frames(args.test))
    print(f"Topomap: {len(topomap)} nodes. Test walk: {len(test_frames)} frames at {args.rate} Hz.")

    for name in args.models:
        print(f"\n== {name}{' (dry run)' if args.dry_run else ''} ==")
        t_load = now()
        runner = build_runner(name, args)
        load_s = now() - t_load
        rows, goal_node = replay(name, runner, topomap, test_frames, args)

        with open(os.path.join(args.out, f"{name}.jsonl"), "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        meta = {
            "model": name, "dry_run": args.dry_run, "steps": len(rows),
            "topomap": os.path.abspath(args.topomap), "test": os.path.abspath(args.test),
            "topomap_nodes": len(topomap), "goal_node": goal_node,
            "test_frames": len(test_frames), "rate_hz": args.rate,
            "context_size": runner.context_size, "load_seconds": round(load_s, 2),
            "weights_mb": runner.weights_mb, "peak_vram_mb": runner.peak_mb(),
            "gpu": runner.gpu_name(), "load_report": runner.load_report,
            "params": {k: getattr(args, k) for k in
                       ("radius", "close_threshold", "waypoint", "num_samples", "seed", "max_v")},
            "host": platform.node(), "python": platform.python_version(),
        }
        try:
            import torch
            meta["torch"] = torch.__version__
            meta["cuda"] = torch.version.cuda
        except ImportError:
            pass
        write_json(os.path.join(args.out, f"{name}.meta.json"), meta)

        lr = runner.load_report or {}
        if lr.get("missing_keys") or lr.get("unexpected_keys"):
            print(f"WARNING: checkpoint mismatch, {lr['missing_keys']} missing and "
                  f"{lr['unexpected_keys']} unexpected keys. Results may be meaningless.")
        last = rows[-1] if rows else {}
        print(f"steps={len(rows)} final_node={last.get('closest_node')}/{goal_node} "
              f"median_ms={np.median([r['ms'] for r in rows]) if rows else 'n/a'} "
              f"peak_vram_mb={meta['peak_vram_mb']}")

        del runner
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass


if __name__ == "__main__":
    main()
