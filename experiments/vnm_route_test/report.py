"""Summarize run_replay.py results into a comparison table and plots.

Example:
  python report.py --results results/test_obstacle --annotations data/test_obstacle/annotations.yaml

Writes <results>/report.md and <results>/report.png and prints the table.

What the offline numbers mean (see README "What this test can and cannot tell you"):
  - node tracking and goal detection: does the model know where it is on the route?
  - obstacle response: do predicted waypoints bend away while an obstacle is in view?
  - latency and VRAM: can it run at the target rate on this GPU?
It cannot measure collisions, because the robot never acts on the outputs.
"""

import argparse
import glob
import json
import os

import numpy as np
import yaml


def load_run(results_dir, name):
    with open(os.path.join(results_dir, f"{name}.meta.json")) as f:
        meta = json.load(f)
    with open(os.path.join(results_dir, f"{name}.jsonl")) as f:
        rows = [json.loads(line) for line in f if line.strip()]
    return meta, rows


def expected_nodes(frames, ann, n_test_frames, goal_node):
    """Expected node per frame: from manual checkpoints if given, else a linear guess."""
    cps = sorted((ann or {}).get("checkpoints") or [], key=lambda c: c["frame"])
    if len(cps) >= 2:
        xs = [c["frame"] for c in cps]
        ys = [c["node"] for c in cps]
        return np.interp(frames, xs, ys), "checkpoints"
    goal_frame = (ann or {}).get("goal_frame", n_test_frames - 1)
    return np.clip(np.asarray(frames) / max(goal_frame, 1) * goal_node, 0, goal_node), "linear guess"


def summarize(meta, rows, ann, args):
    frames = np.array([r["frame"] for r in rows])
    nodes = np.array([r["closest_node"] for r in rows])
    lateral = np.array([r["waypoint_norm"][1] for r in rows]) * args.lateral_sign
    ms = np.array([r["ms"] for r in rows])
    goal = meta["goal_node"]
    n_test = meta["test_frames"]
    rate = meta["rate_hz"]

    exp, exp_src = expected_nodes(frames, ann, n_test, goal)
    goal_frame = (ann or {}).get("goal_frame", n_test - 1)
    tol = args.goal_tolerance_s * rate
    reached = np.where(nodes == goal)[0]
    first_goal = int(frames[reached[0]]) if len(reached) else None

    s = {
        "model": meta["model"] + (" (dry run)" if meta.get("dry_run") else ""),
        "steps": len(rows),
        "final_node": f"{int(nodes[-1])}/{goal}" if len(rows) else "n/a",
        "reached_goal": bool(len(reached)),
        "premature_goal": bool(first_goal is not None and first_goal < goal_frame - tol),
        "goal_frame_error_s": None if first_goal is None else round((first_goal - goal_frame) / rate, 2),
        "node_mae": round(float(np.mean(np.abs(nodes - exp))), 2),
        "node_mae_source": exp_src,
        "backward_jumps": int(np.sum(np.diff(nodes) < 0)),
        "ms_p50": round(float(np.percentile(ms, 50)), 2),
        "ms_p95": round(float(np.percentile(ms, 95)), 2),
        "max_hz_p95": round(1000.0 / max(np.percentile(ms, 95), 1e-6), 1),
        "peak_vram_mb": None if meta.get("peak_vram_mb") is None else round(meta["peak_vram_mb"], 1),
        "load_mismatch": (meta.get("load_report") or {}).get("missing_keys", 0)
                         + (meta.get("load_report") or {}).get("unexpected_keys", 0),
    }

    # obstacle response: lateral offset inside obstacle segments vs. outside
    segs = (ann or {}).get("obstacles") or []
    if segs:
        inside = np.zeros(len(frames), dtype=bool)
        for seg in segs:
            inside |= (frames >= seg["start"]) & (frames <= seg["end"])
        base = float(np.median(lateral[~inside])) if (~inside).any() else 0.0
        away, shifts = 0, []
        for seg in segs:
            m = (frames >= seg["start"]) & (frames <= seg["end"])
            if not m.any():
                continue
            shift = float(np.mean(lateral[m]) - base)
            shifts.append(shift)
            # y > 0 is left: an obstacle on the left should push waypoints right (shift < 0)
            want = -1 if seg["side"] == "left" else 1
            away += int(np.sign(shift) == want and abs(shift) >= args.min_shift)
        s["obstacle_segments"] = len(shifts)
        s["steered_away"] = f"{away}/{len(shifts)}"
        s["mean_abs_shift"] = round(float(np.mean(np.abs(shifts))), 3) if shifts else None
    s["_series"] = (frames, nodes, exp, lateral)
    return s


COLUMNS = [
    ("model", "Model"), ("final_node", "Final node"), ("reached_goal", "Reached goal"),
    ("premature_goal", "Early goal call"), ("goal_frame_error_s", "Goal timing error (s)"),
    ("node_mae", "Node error (MAE)"), ("backward_jumps", "Backward jumps"),
    ("steered_away", "Steered away"), ("mean_abs_shift", "Mean lateral shift"),
    ("ms_p50", "Latency p50 (ms)"), ("ms_p95", "Latency p95 (ms)"),
    ("max_hz_p95", "Max rate at p95 (Hz)"), ("peak_vram_mb", "Peak VRAM (MB)"),
    ("load_mismatch", "Checkpoint key mismatches"),
]


def to_markdown(summaries):
    cols = [c for c in COLUMNS if any(c[0] in s for s in summaries)]
    lines = ["| " + " | ".join(h for _, h in cols) + " |",
             "|" + "---|" * len(cols)]
    for s in summaries:
        lines.append("| " + " | ".join("—" if s.get(k) is None else str(s.get(k, "—")) for k, _ in cols) + " |")
    return "\n".join(lines)


def plot(summaries, ann, path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping plot")
        return
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    for s in summaries:
        frames, nodes, exp, lateral = s["_series"]
        a1.step(frames, nodes, where="post", label=s["model"])
        a2.plot(frames, lateral, label=s["model"])
    if summaries:
        frames, _, exp, _ = summaries[0]["_series"]
        a1.plot(frames, exp, "k--", lw=1, label=f"expected ({summaries[0]['node_mae_source']})")
    for seg in (ann or {}).get("obstacles") or []:
        for ax in (a1, a2):
            ax.axvspan(seg["start"], seg["end"], color="orange", alpha=0.2)
    a1.set_ylabel("closest topomap node")
    a2.set_ylabel("lateral waypoint (+ = left)")
    a2.set_xlabel("test frame")
    a2.axhline(0, color="grey", lw=0.5)
    a1.legend(fontsize=8)
    a1.set_title("Orange: obstacle in view (from annotations)")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--results", required=True)
    p.add_argument("--annotations", help="YAML with checkpoints / obstacles / goal_frame")
    p.add_argument("--goal-tolerance-s", type=float, default=2.0,
                   help="goal called this many seconds early still counts as on time (default 2)")
    p.add_argument("--min-shift", type=float, default=0.05,
                   help="smallest lateral shift (normalized units) that counts as steering (default 0.05)")
    p.add_argument("--lateral-sign", type=float, default=1.0, choices=[1.0, -1.0],
                   help="set -1 if waypoints turn out to use y = right")
    args = p.parse_args()

    ann = None
    if args.annotations:
        with open(args.annotations) as f:
            ann = yaml.safe_load(f)

    names = sorted(os.path.basename(m)[:-len(".meta.json")]
                   for m in glob.glob(os.path.join(args.results, "*.meta.json")))
    if not names:
        raise SystemExit(f"No results in {args.results}")
    summaries = [summarize(*load_run(args.results, n), ann, args) for n in names]

    table = to_markdown(summaries)
    notes = [
        f"Results: `{os.path.abspath(args.results)}`",
        f"Annotations: `{os.path.abspath(args.annotations)}`" if args.annotations else
        "Annotations: none (node error uses a linear time guess; no obstacle scoring)",
        "",
        "Open-loop replay: the robot never acted on these outputs, so collisions are not measured.",
    ]
    if any(s["model"].endswith("(dry run)") for s in summaries):
        notes.append("**Dry run: a numpy stand-in produced these numbers. They say nothing about the real models.**")
    out_md = os.path.join(args.results, "report.md")
    with open(out_md, "w") as f:
        f.write("# Offline route test report\n\n" + "\n".join(notes) + "\n\n" + table + "\n")
    plot(summaries, ann, os.path.join(args.results, "report.png"))
    print(table)
    print(f"\nWrote {out_md} and report.png")


if __name__ == "__main__":
    main()
