"""Turn a recorded walk (video file or image folder) into evenly timed frames.

Examples:
  python extract_frames.py --src walk_route.mp4 --out data/route --fps 4
  python extract_frames.py --src realsense_pngs/ --src-fps 30 --out data/test_obstacle --fps 4

Writes numbered PNGs (000000.png, 000001.png, ...) and meta.json with the
output frame rate, which build_topomap.py and run_replay.py read.
"""

import argparse
import os

import cv2

from common import IMAGE_EXTENSIONS, list_frames, write_json


def resize_keep_aspect(img, max_width):
    h, w = img.shape[:2]
    if max_width and w > max_width:
        img = cv2.resize(img, (max_width, round(h * max_width / w)), interpolation=cv2.INTER_AREA)
    return img


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--src", required=True, help="video file or folder of images")
    p.add_argument("--out", required=True, help="output folder (must be empty or new)")
    p.add_argument("--fps", type=float, default=4.0,
                   help="output frame rate; use the rate the model will run at (default 4)")
    p.add_argument("--src-fps", type=float, default=None,
                   help="frame rate of an image-folder source (required for folders)")
    p.add_argument("--max-width", type=int, default=640, help="downscale wider frames (default 640)")
    p.add_argument("--start", type=float, default=0.0, help="skip this many seconds at the start")
    p.add_argument("--end", type=float, default=None, help="stop at this time in seconds")
    args = p.parse_args()

    os.makedirs(args.out, exist_ok=True)
    if any(n.lower().endswith(IMAGE_EXTENSIONS) for n in os.listdir(args.out)):
        raise SystemExit(f"{args.out} already contains images; use a new folder")

    if os.path.isdir(args.src):
        if not args.src_fps:
            raise SystemExit("--src-fps is required when --src is a folder")
        paths = list_frames(args.src)
        src_fps = args.src_fps
        reader = ((i, cv2.imread(pth)) for i, pth in enumerate(paths))
        total = len(paths)
    else:
        cap = cv2.VideoCapture(args.src)
        if not cap.isOpened():
            raise SystemExit(f"Could not open video {args.src}")
        src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        def video_frames():
            i = 0
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                yield i, frame
                i += 1
            cap.release()

        reader = video_frames()

    step = 1.0 / args.fps
    next_t = args.start
    written = 0
    for i, frame in reader:
        if frame is None:
            continue
        t = i / src_fps
        if args.end is not None and t > args.end:
            break
        if t + 1e-9 < next_t:
            continue
        cv2.imwrite(os.path.join(args.out, f"{written:06d}.png"), resize_keep_aspect(frame, args.max_width))
        written += 1
        next_t += step

    write_json(os.path.join(args.out, "meta.json"), {
        "fps": args.fps, "source": os.path.abspath(args.src), "source_fps": src_fps,
        "source_frames": total, "frames": written, "start_s": args.start, "end_s": args.end,
    })
    print(f"Wrote {written} frames at {args.fps} fps to {args.out}")


if __name__ == "__main__":
    main()
