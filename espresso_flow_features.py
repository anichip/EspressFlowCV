import os
import cv2
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

# ---------------------------
# Configuration dataclasses
# ---------------------------

@dataclass
class ROIConfig:
    # Fractional ROI (x0, y0, x1, y1) relative to frame size
    x0: float = 0.32
    y0: float = 0.15
    x1: float = 0.68
    y1: float = 0.80


@dataclass
class Thresholds:
    # Motion
    flow_mag_thresh: float = 1.2
    min_area: int = 150   # in pixels, after ROI
    min_height: int = 25  # bounding box height
    min_aspect: float = 1.6  # h/w ratio (tall & thin)
    # Color (HSV in OpenCV ranges: H:0..180, S:0..255, V:0..255)
    h_lo: int = 5     # "brown/amber" lower hue
    h_hi: int = 30    # "brown/amber" upper hue
    s_lo: int = 40
    v_lo: int = 20
    v_hi: int = 230
    # Post timelines
    onset_area_px: int = 300  # first time the detected component reaches this area, we say 'flow starts'


@dataclass
class DebugConfig:
    save_overlay_video: bool = True
    overlay_fps: int = 30
    save_kymograph: bool = True


@dataclass
class FrameStats:
    stream_found: bool
    area: int
    width: int
    height: int
    cx: float
    cy: float
    hue_med: float
    val_med: float


# ---------------------------
# Utilities
# ---------------------------

def _roi_rect(shape, roi_cfg: ROIConfig) -> Tuple[int, int, int, int]:
    H, W = shape[:2]
    x0 = int(W * roi_cfg.x0)
    y0 = int(H * roi_cfg.y0)
    x1 = int(W * roi_cfg.x1)
    y1 = int(H * roi_cfg.y1)
    return x0, y0, x1, y1


def _component_score(cx, roi_w, area):
    center = roi_w / 2.0
    dist = abs(cx - center) / max(1.0, roi_w / 2.0)
    return area * (1.0 - 0.7 * dist)


def _best_component(contours, roi_w, thr: Thresholds):
    best = None
    best_score = 0.0
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if h < thr.min_height or w < 2:
            continue
        area = int(cv2.contourArea(c))
        if area < thr.min_area:
            continue
        aspect = h / max(1.0, w)
        if aspect < thr.min_aspect:
            continue
        cx = x + w / 2.0
        score = _component_score(cx, roi_w, area)
        if score > best_score:
            best_score = score
            best = (x, y, w, h, area, cx, y + h/2.0)
    return best


def _make_kymograph(columns_over_time: List[np.ndarray]) -> np.ndarray:
    if not columns_over_time:
        return np.zeros((10, 10), dtype=np.uint8)
    M = np.stack(columns_over_time, axis=0)
    M = M.astype(np.float32)
    row_min = M.min(axis=1, keepdims=True)
    row_max = M.max(axis=1, keepdims=True)
    Mn = (M - row_min) / np.maximum(1e-6, (row_max - row_min))
    return (Mn * 255).astype(np.uint8)


# ---------------------------
# Core per-frame segmentation
# ---------------------------

class EspressoStreamSegmenter:
    def __init__(self, roi_cfg: ROIConfig, thr: Thresholds):
        self.roi_cfg = roi_cfg
        self.thr = thr
        self.prev_gray_roi = None

    def segment(self, frame_bgr: np.ndarray) -> Tuple[FrameStats, np.ndarray, Tuple[int,int,int,int]]:
        H, W = frame_bgr.shape[:2]
        x0, y0, x1, y1 = _roi_rect(frame_bgr.shape, self.roi_cfg)
        roi = frame_bgr[y0:y1, x0:x1]
        roi_h, roi_w = roi.shape[:2]

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        if self.prev_gray_roi is None or self.prev_gray_roi.shape != gray.shape:
            flow_mag = np.zeros_like(gray, dtype=np.float32)
        else:
            flow = cv2.calcOpticalFlowFarneback(self.prev_gray_roi, gray,
                                                None, 0.5, 3, 15, 3, 5, 1.2, 0)
            fx, fy = flow[..., 0], flow[..., 1]
            flow_mag = np.sqrt(fx * fx + fy * fy)

        self.prev_gray_roi = gray

        motion_mask = (flow_mag > self.thr.flow_mag_thresh).astype(np.uint8) * 255
        motion_mask = cv2.dilate(motion_mask, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 5)), 1)

        color_mask = cv2.inRange(hsv,
                                 (self.thr.h_lo, self.thr.s_lo, self.thr.v_lo),
                                 (self.thr.h_hi, 255, self.thr.v_hi))

        stream_mask = cv2.bitwise_and(motion_mask, color_mask)

        contours, _ = cv2.findContours(stream_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best = _best_component(contours, roi_w, self.thr)

        if best is None:
            return FrameStats(False, 0, 0, 0, -1, -1, np.nan, np.nan), stream_mask, (x0, y0, x1, y1)

        x, y, w, h, area, cx, cy = best

        comp_mask = np.zeros_like(stream_mask)
        cv2.rectangle(comp_mask, (x, y), (x + w, y + h), 255, -1)
        comp_mask = cv2.bitwise_and(comp_mask, stream_mask)

        comp_inds = comp_mask > 0
        hue_med = float(np.median(hsv[...,0][comp_inds])) if np.any(comp_inds) else np.nan
        val_med = float(np.median(hsv[...,2][comp_inds])) if np.any(comp_inds) else np.nan

        return FrameStats(True, int(area), int(w), int(h), float(cx), float(cy), hue_med, val_med), stream_mask, (x0, y0, x1, y1)


# ---------------------------
# Timeline feature extraction
# ---------------------------

def _first_onset(area_t: List[int], px_thresh: int) -> Optional[int]:
    for i, a in enumerate(area_t):
        if a >= px_thresh:
            return i
    return None


def _slope(y: np.ndarray) -> float:
    if len(y) < 2:
        return 0.0
    x = np.arange(len(y), dtype=np.float32)
    A = np.vstack([x, np.ones_like(x)]).T
    m, b = np.linalg.lstsq(A, y.astype(np.float32), rcond=None)[0]
    return float(m)


def _cv(x: np.ndarray) -> float:
    mu = np.mean(x) if len(x) else 0.0
    sd = np.std(x) if len(x) else 0.0
    return float(sd / (mu + 1e-6))


def extract_features_from_timelines(width_t: List[int],
                                    area_t: List[int],
                                    cx_t: List[float],
                                    hue_t: List[float],
                                    val_t: List[float],
                                    fps: int) -> Dict[str, float]:
    W = np.array(width_t, dtype=np.float32)
    A = np.array(area_t, dtype=np.float32)
    CX = np.array(cx_t, dtype=np.float32)
    H = np.array(hue_t, dtype=np.float32)
    V = np.array(val_t, dtype=np.float32)

    onset = _first_onset(area_t, px_thresh=Thresholds().onset_area_px)
    onset_time = (onset / fps) if onset is not None else np.nan

    if onset is not None:
        W2, A2, CX2, H2, V2 = W[onset:], A[onset:], CX[onset:], H[onset:], V[onset:]
    else:
        W2, A2, CX2, H2, V2 = W, A, CX, H, V

    cont = float(np.mean(A2 > Thresholds().onset_area_px)) if len(A2) else 0.0

    mean_w = float(np.mean(W2)) if len(W2) else 0.0
    cv_w = _cv(W2) if len(W2) else 0.0
    amp_w = float(np.max(W2) - np.min(W2)) if len(W2) else 0.0
    slope_w = _slope(W2) if len(W2) else 0.0
    jitter_cx = float(np.std(CX2)) if len(CX2) else 0.0

    def thirds_delta(arr):
        if len(arr) < 9:
            return np.nan
        n = len(arr)
        a = np.nanmedian(arr[: n//3])
        b = np.nanmedian(arr[- n//3:])
        return float(b - a)

    val_delta = thirds_delta(V2)
    hue_delta = thirds_delta(H2)

    if len(A2) > 3:
        onoff = (A2 > Thresholds().onset_area_px).astype(np.int32)
        flicker = int(np.sum(np.abs(np.diff(onoff)) == 1))
    else:
        flicker = 0

    return {
        "onset_time_s": onset_time,
        "continuity": cont,
        "mean_width": mean_w,
        "cv_width": cv_w,
        "amp_width": amp_w,
        "slope_width": slope_w,
        "jitter_cx": jitter_cx,
        "delta_val": val_delta,
        "delta_hue": hue_delta,
        "flicker": float(flicker),
    }


def simple_rule_classifier(features: Dict[str, float]) -> str:
    cont = features["continuity"]
    mean_w = features["mean_width"]
    cv_w = features["cv_width"]
    val_delta = features["delta_val"]
    slope_w = features["slope_width"]

    if (cont < 0.55 and mean_w < 6) or (val_delta is not None and not np.isnan(val_delta) and val_delta > -5):
        return "underextracted"
    if (val_delta is not None and not np.isnan(val_delta) and val_delta < -25) and slope_w < -0.02:
        return "overextracted"
    if cont >= 0.7 and cv_w < 0.35 and mean_w >= 6:
        return "perfect_or_mid"

    return "mid"


# ---------------------------
# Visualization Debugger Helper function
# ---------------------------

def _make_kymograph(columns_over_time: List[np.ndarray]) -> np.ndarray:
    """Build a (time x width) kymograph from per-frame column intensity sums."""
    if not columns_over_time:
        return np.zeros((10, 10), dtype=np.uint8)
    M = np.stack(columns_over_time, axis=0).astype(np.float32)  # [T, W]
    # normalize each row 0..255 for visibility
    row_min = M.min(axis=1, keepdims=True)
    row_max = M.max(axis=1, keepdims=True)
    Mn = (M - row_min) / np.maximum(1e-6, (row_max - row_min))
    return (Mn * 255).astype(np.uint8)

# ---------------------------
# Main pipeline for a folder of frames
# ---------------------------

def process_frames_folder(folder: str,
                          fps: int = 60,
                          max_seconds: float = 7.0,
                          roi_cfg: ROIConfig = ROIConfig(),
                          thr: Thresholds = Thresholds(),
                          debug: DebugConfig = DebugConfig()) -> Dict[str, float]:
    
    frame_files = sorted([f for f in os.listdir(folder) if f.lower().endswith(".jpg")])
    if not frame_files:
        raise FileNotFoundError(f"No .jpg frames found in {folder}")

    max_frames = int(fps * max_seconds)
    frame_files = frame_files[:max_frames]

    seg = EspressoStreamSegmenter(roi_cfg, thr)

    width_t, area_t, cx_t, hue_t, val_t = [], [], [], [], []
    columns_for_kymo: List[np.ndarray] = []
    writer = None  # Initialize VideoWriter for debug overlay

    for idx, fname in enumerate(frame_files):
        path = os.path.join(folder, fname)
        frame = cv2.imread(path)
        if frame is None:
            continue

        stats, stream_mask, roi_rect = seg.segment(frame)
        x0, y0, x1, y1 = roi_rect

        #accumulate time series
        width_t.append(stats.width)
        area_t.append(stats.area)
        cx_t.append(stats.cx)
        hue_t.append(stats.hue_med)
        val_t.append(stats.val_med)

        #collect columns for kymograph (darker --> larger)
        if debug.save_kymograph:
            roi = frame[y0:y1, x0:x1]
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            columns_for_kymo.append(np.sum(255 - gray, axis=0))

        #write the debug overlay video to evaluate
        if debug.save_overlay_video:
            overlay = frame.copy()
            # draw ROI
            cv2.rectangle(overlay, (x0, y0), (x1, y1), (0, 255, 0), 2)
            # draw detected stream bbox (project ROI coords back to full image)
            if stats.stream_found and stats.width > 0 and stats.height > 0:
                rx = int(x0 + stats.cx - stats.width / 2)
                ry = int(y0 + stats.cy - stats.height / 2)
                cv2.rectangle(overlay, (rx, ry), (rx + stats.width, ry + stats.height), (255, 0, 0), 2)
            # HUD text
            vtxt = "nan" if np.isnan(stats.val_med) else f"{stats.val_med:.1f}"
            txt = f"W:{stats.width} A:{stats.area} Vmed:{vtxt}"
            cv2.putText(overlay, txt, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            if writer is None:
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                out_path = os.path.join(folder, "_debug_overlay.mp4")
                writer = cv2.VideoWriter(out_path, fourcc, debug.overlay_fps, (overlay.shape[1], overlay.shape[0]))
            writer.write(overlay)

    if writer is not None:
        writer.release()

    # save kymograph image
    if debug.save_kymograph and len(columns_for_kymo) > 5:
        kymo = _make_kymograph(columns_for_kymo)
        kymo_path = os.path.join(folder, "_kymograph.png")
        cv2.imwrite(kymo_path, kymo)

    feats = extract_features_from_timelines(width_t, area_t, cx_t, hue_t, val_t, fps=fps)
    feats["label_rule_based"] = simple_rule_classifier(feats)
    return feats
