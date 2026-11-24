"""Build a topological map from the frames of a route recording.

Mirrors upstream create_topomap.py: one node every --dt seconds, saved as
0.png, 1.png, ... (upstream's default is dt = 1 s).

Example:
  python build_topomap.py --frames data/route --out data/topomap --dt 1.0
"""

import argparse
import os
import shutil

from common import list_frames, read_meta, write_json


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--frames", required=True, help="folder written by extract_frames.py")
    p.add_argument("--out", required=True, help="topomap folder to create")
    p.add_argument("--dt", type=float, default=1.0, help="seconds between nodes (default 1.0)")
    p.add_argument("--fps", type=float, default=None, help="frame rate if meta.json is missing")
    args = p.parse_args()

    fps = args.fps or read_meta(args.frames).get("fps")
    if not fps:
        raise SystemExit("Frame rate unknown: pass --fps or use extract_frames.py output")
    paths = list_frames(args.frames)
    stride = max(1, round(args.dt * fps))

    if os.path.exists(args.out) and os.listdir(args.out):
        raise SystemExit(f"{args.out} is not empty; choose a new folder")
    os.makedirs(args.out, exist_ok=True)

    chosen = paths[::stride]
    if paths[-1] not in chosen:  # always keep the final view as the goal node
        chosen.append(paths[-1])
    for node, src in enumerate(chosen):
        shutil.copyfile(src, os.path.join(args.out, f"{node}.png"))

    write_json(os.path.join(args.out, "meta.json"), {
        "dt": args.dt, "frames_fps": fps, "stride_frames": stride, "nodes": len(chosen),
        "source_frames": os.path.abspath(args.frames),
        "node_source_frame": [int(os.path.splitext(os.path.basename(c))[0]) for c in chosen],
    })
    print(f"Wrote {len(chosen)} nodes (every {stride} frames) to {args.out}")


if __name__ == "__main__":
    main()
