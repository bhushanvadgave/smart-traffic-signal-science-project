"""
count_per_region.py

Classical computer-vision object counting per region (no ML).
- Works best for toy cars on a plain background with consistent lighting.
- Modes: threshold-based blob detection (default), HSV color-based detection (optional),
  or simple background-subtraction mode (optional).

Usage:
    python count_per_region.py           # webcam (index 0)
    python count_per_region.py --src 1   # webcam index 1
    python count_per_region.py --src path/to/image.jpg

Dependencies:
    pip install opencv-python numpy

Keys while running (webcam mode):
    q     -> quit
    =     -> decrease MIN_CONTOUR_AREA (more sensitive)
    -     -> increase MIN_CONTOUR_AREA (less sensitive)
    c     -> toggle color-detection mode (HSV) on/off
    b     -> toggle background-subtraction mode on/off
    s     -> save current frame + mask to files (useful for tuning)
    l     -> toggle logging counts to CSV (appends to counts_log.csv)

Tune parameters near top of file to match your setup.
"""

import cv2
import numpy as np
import argparse
import time
import os
import csv

# ---------------- CONFIG ----------------
MIN_CONTOUR_AREA = 300        # tune: smaller = more sensitive; larger = ignore small blobs
BLUR_KERNEL = (7, 7)
ADAPTIVE_THRESH_BLOCK = 51
ADAPTIVE_C = 7

USE_COLOR_MODE_BY_DEFAULT = False
USE_BG_SUBTRACT_BY_DEFAULT = False

# HSV color detection defaults (if you mark toy-cars with a colored dot)
# These example ranges detect a red sticker. Tune using trackbars if needed.
HSV_LOW = np.array([0, 100, 100])
HSV_HIGH = np.array([10, 255, 255])

# Logging
LOG_FILENAME = "counts_log.csv"
# ----------------------------------------

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def detect_by_threshold(frame, min_contour_area=MIN_CONTOUR_AREA):
    """Classic threshold + morphology + contour detection."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, BLUR_KERNEL, 0)

    thresh = cv2.adaptiveThreshold(blur, 255,
                                   cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV,
                                   ADAPTIVE_THRESH_BLOCK, ADAPTIVE_C)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
    morph = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
    morph = cv2.morphologyEx(morph, cv2.MORPH_CLOSE, kernel, iterations=1)

    contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_contour_area:
            continue
        x,y,w,h = cv2.boundingRect(cnt)
        cx = x + w//2
        cy = y + h//2
        boxes.append((x,y,w,h,area,cx,cy))
    return boxes, morph

def detect_by_color(frame, hsv_low=HSV_LOW, hsv_high=HSV_HIGH, min_contour_area=MIN_CONTOUR_AREA):
    """Detect by HSV color range. Useful if you add a colored sticker to each toy car."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, hsv_low, hsv_high)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7,7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_contour_area:
            continue
        x,y,w,h = cv2.boundingRect(cnt)
        cx = x + w//2
        cy = y + h//2
        boxes.append((x,y,w,h,area,cx,cy))
    return boxes, mask

def process_and_draw(frame, boxes, mask, split_x=None):
    """Draw bounding boxes, center points, region divider, and counts overlay."""
    vis = frame.copy()
    h, w = frame.shape[:2]
    if split_x is None:
        split_x = w // 2
    # draw vertical divider
    cv2.line(vis, (split_x, 0), (split_x, h), (255, 0, 0), 2)

    left_count = 0
    right_count = 0

    for (x,y,ww,hh,area,cx,cy) in boxes:
        # bounding box
        cv2.rectangle(vis, (x,y), (x+ww, y+hh), (0,255,0), 2)
        # center
        cv2.circle(vis, (cx,cy), 3, (0,0,255), -1)
        # count assignment
        if cx < split_x:
            left_count += 1
            cv2.putText(vis, "L", (x, y-6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 2)
        else:
            right_count += 1
            cv2.putText(vis, "R", (x, y-6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 2)

    cv2.putText(vis, f"Left: {left_count}", (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,255), 2)
    cv2.putText(vis, f"Right: {right_count}", (w-240,30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,255), 2)
    return vis, left_count, right_count, mask

def write_log(timestamp, left_count, right_count, filename=LOG_FILENAME):
    exists = os.path.isfile(filename)
    with open(filename, "a", newline="") as f:
        writer = csv.writer(f)
        if not exists:
            writer.writerow(["timestamp", "left_count", "right_count"])
        writer.writerow([timestamp, left_count, right_count])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", help="Video source: 0 (default) for webcam or path to image/video or webcam index", default="0")
    parser.add_argument("--min_area", type=int, default=MIN_CONTOUR_AREA, help="Minimum contour area")
    parser.add_argument("--split_ratio", type=float, default=0.5, help="Vertical split ratio (0..1); default 0.5 = center")
    parser.add_argument("--color_low", nargs=3, type=int, help="HSV low (e.g. 0 100 100) for color mode")
    parser.add_argument("--color_high", nargs=3, type=int, help="HSV high (e.g. 10 255 255) for color mode")
    args = parser.parse_args()

    src = args.src
    min_area = args.min_area
    split_ratio = args.split_ratio
    color_low = np.array(args.color_low) if args.color_low else HSV_LOW
    color_high = np.array(args.color_high) if args.color_high else HSV_HIGH

    use_color = USE_COLOR_MODE_BY_DEFAULT
    use_bg_sub = USE_BG_SUBTRACT_BY_DEFAULT
    logging_on = False

    # Determine if src is a number (webcam index) or path
    if src.isdigit():
        src_idx = int(src)
        cap = cv2.VideoCapture(src_idx)
    else:
        if os.path.exists(src):
            cap = cv2.VideoCapture(src)
        else:
            print("Source not found. Trying to open as webcam index 0.")
            cap = cv2.VideoCapture(0)

    # background subtractor
    bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=100, varThreshold=40, detectShadows=False)

    if not cap.isOpened():
        print("Cannot open source:", src)
        return

    print("Controls: q=quit, =/- adjust sensitivity, c=toggle color mode, b=toggle bg-sub, s=save frame, l=toggle logging")
    frame_idx = 0
    ensure_dir("snapshots")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1
        h, w = frame.shape[:2]
        split_x = int(w * split_ratio)

        if use_bg_sub:
            fgmask = bg_subtractor.apply(frame)
            # clean
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
            mask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel, iterations=1)
            # find contours on mask
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            boxes = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < min_area:
                    continue
                x,y,ww,hh = cv2.boundingRect(cnt)
                cx = x + ww//2
                cy = y + hh//2
                boxes.append((x,y,ww,hh,area,cx,cy))
            vis, left_count, right_count, display_mask = process_and_draw(frame, boxes, mask, split_x)
        else:
            if use_color:
                boxes, mask = detect_by_color(frame, hsv_low=color_low, hsv_high=color_high, min_contour_area=min_area)
            else:
                boxes, mask = detect_by_threshold(frame, min_contour_area=min_area)
            vis, left_count, right_count, display_mask = process_and_draw(frame, boxes, mask, split_x)

        # Decide result
        if left_count > right_count:
            decision = f"Left more. Left {left_count}, Right {right_count}"
        elif right_count > left_count:
            decision = f"Right more. Left {left_count}, Right {right_count}"
        else:
            decision = f"Same. Left {left_count}, Right {right_count}"

        # Print to console
        print("Decision:", decision)

        # Overlay on frame
        cv2.putText(vis, decision, (10, h-20), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 2)

        ######################
        cv2.imshow("Frame", vis)
        cv2.imshow("Mask", display_mask)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('='):
            min_area = max(10, min_area - 50)
            print("MIN_CONTOUR_AREA ->", min_area)
        elif key == ord('-'):
            min_area += 50
            print("MIN_CONTOUR_AREA ->", min_area)
        elif key == ord('c'):
            use_color = not use_color
            print("Color mode ->", use_color)
        elif key == ord('b'):
            use_bg_sub = not use_bg_sub
            print("Background-subtraction mode ->", use_bg_sub)
        elif key == ord('s'):
            t = int(time.time())
            cv2.imwrite(f"snapshots/frame_{t}.jpg", frame)
            cv2.imwrite(f"snapshots/mask_{t}.png", display_mask)
            print("Saved snapshots to snapshots/")
        elif key == ord('l'):
            logging_on = not logging_on
            print("Logging ->", logging_on)

        if logging_on:
            write_log(time.strftime("%Y-%m-%d %H:%M:%S"), left_count, right_count)

    cap.release()
    cv2.destroyAllWindows()
    print("Exited cleanly.")

if __name__ == "__main__":
    main()
