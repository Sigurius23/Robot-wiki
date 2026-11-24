"""Generate a synthetic corridor walk for checking the pipeline (no real data).

Creates route.mp4, test.mp4 (same corridor, slower, darker, with a dark
obstacle on the left for part of the walk) and annotations.yaml whose frame
numbers match extract_frames.py output at --fps.

Example:
  python make_synthetic.py --out data/synth --fps 4
"""

import argparse
import os

import cv2
import numpy as np
import yaml

W, H = 320, 240
LENGTH_M = 15.0


def render(s, brightness=1.0, obstacle=False, rng=None):
    """Corridor view at distance s (metres) along the route."""
    img = np.zeros((H, W, 3), np.float32)
    img[: H // 2] = (0.55, 0.55, 0.6)                              # ceiling
    img[H // 2:] = np.linspace(0.3, 0.5, H - H // 2)[:, None, None]  # floor
    # wall panels whose colours change along the route, so places look different
    for k in range(8):
        pos = int(s * 2) + k
        colour = np.array([(pos * 37) % 255, (pos * 91) % 255, (pos * 53) % 255], np.float32) / 255
        x0 = int((k * 40 - (s * 80) % 40))
        img[60:180, max(x0, 0):max(x0 + 30, 0)] = colour
    if obstacle:
        img[110:230, 20:140] = 0.05                                  # dark box on the left
    img *= brightness
    if rng is not None:
        img += rng.normal(0, 0.02, img.shape)
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)


def write_video(path, frames, fps):
    vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))
    for f in frames:
        vw.write(f)
    vw.release()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", required=True)
    p.add_argument("--fps", type=float, default=4.0, help="rate you will pass to extract_frames.py")
    p.add_argument("--video-fps", type=int, default=30)
    p.add_argument("--dt", type=float, default=1.0, help="topomap node spacing you will use")
    args = p.parse_args()
    os.makedirs(args.out, exist_ok=True)
    rng = np.random.default_rng(0)

    v_route, v_test = 0.5, 0.45                     # m/s
    obstacle_m = (6.0, 8.0)

    n_route = int(LENGTH_M / v_route * args.video_fps)
    route = [render(i / args.video_fps * v_route, rng=rng) for i in range(n_route + 1)]
    write_video(os.path.join(args.out, "route.mp4"), route, args.video_fps)

    n_test = int(LENGTH_M / v_test * args.video_fps)
    test = []
    for i in range(n_test + 1):
        s = i / args.video_fps * v_test
        test.append(render(s, brightness=0.9, obstacle=obstacle_m[0] <= s <= obstacle_m[1], rng=rng))
    write_video(os.path.join(args.out, "test.mp4"), test, args.video_fps)

    # frame indices after extract_frames.py --fps args.fps
    def frame_at(s):
        return int(round(s / v_test * args.fps))

    def node_at(s):
        return int(round(s / (v_route * args.dt)))

    ann = {
        "note": "synthetic walk; frames refer to extract_frames.py output at fps=%g" % args.fps,
        "goal_frame": frame_at(LENGTH_M),
        "checkpoints": [{"frame": frame_at(s), "node": node_at(s)} for s in np.arange(0, LENGTH_M + 0.01, 3.0)],
        "obstacles": [{"start": frame_at(obstacle_m[0]), "end": frame_at(obstacle_m[1]), "side": "left"}],
    }
    with open(os.path.join(args.out, "annotations.yaml"), "w") as f:
        yaml.safe_dump(ann, f, sort_keys=False)
    print(f"Wrote route.mp4 ({len(route)} frames), test.mp4 ({len(test)} frames) and annotations.yaml to {args.out}")


if __name__ == "__main__":
    main()
