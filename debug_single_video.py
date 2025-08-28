#!/usr/bin/env python3
"""
Generate debug overlay for a single video to test reflection fixes
without running full feature extraction
"""
import os
import cv2
import sys
from espresso_flow_features import (
    ROIConfig, 
    Thresholds, 
    DebugConfig, 
    EspressoStreamSegmenter
)

def generate_debug_overlay(video_path: str, output_path: str = None):
    """
    Generate debug overlay video for a single input video
    Shows ROI box, detected streams, and measurements like the main pipeline
    """
    
    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        return
    
    # Use same config as main pipeline
    roi_cfg = ROIConfig()
    thr = Thresholds()
    debug = DebugConfig(save_overlay_video=True, overlay_fps=30)
    
    # Initialize segmenter
    seg = EspressoStreamSegmenter(roi_cfg, thr)
    
    # Open input video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video: {video_path}")
        return
    
    # Get video properties
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"Processing: {os.path.basename(video_path)}")
    print(f"Resolution: {width}x{height}")
    print(f"FPS: {fps}, Total frames: {total_frames}")
    
    # Setup output path
    if output_path is None:
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_path = f"{base_name}_debug_overlay.mp4"
    
    # Initialize video writer
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, debug.overlay_fps, (width, height))
    
    frame_idx = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Process frame with same logic as main pipeline
            stats, stream_mask, roi_rect = seg.segment(frame)
            x0, y0, x1, y1 = roi_rect
            
            # Create overlay (same as main pipeline)
            overlay = frame.copy()
            
            # Draw ROI box (green)
            cv2.rectangle(overlay, (x0, y0), (x1, y1), (0, 255, 0), 2)
            
            # Draw detected stream bbox (blue) - project ROI coords back to full image
            if stats.stream_found and stats.width > 0 and stats.height > 0:
                rx = int(x0 + stats.cx - stats.width / 2)
                ry = int(y0 + stats.cy - stats.height / 2)
                cv2.rectangle(overlay, (rx, ry), (rx + stats.width, ry + stats.height), (255, 0, 0), 2)
            
            # Add HUD text with measurements
            vtxt = "nan" if stats.val_med != stats.val_med else f"{stats.val_med:.1f}"  # NaN check
            txt = f"W:{stats.width} A:{stats.area} Vmed:{vtxt}"
            cv2.putText(overlay, txt, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Add frame counter
            frame_txt = f"Frame: {frame_idx}/{total_frames}"
            cv2.putText(overlay, frame_txt, (12, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            writer.write(overlay)
            frame_idx += 1
            
            # Progress indicator
            if frame_idx % 30 == 0:
                progress = (frame_idx / total_frames) * 100
                print(f"Progress: {progress:.1f}%")
    
    finally:
        cap.release()
        writer.release()
    
    print(f"Debug overlay saved to: {output_path}")
    print("Green box = ROI, Blue box = detected stream")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_single_video.py <video_path> [output_path]")
        print("\nExample:")
        print("  python debug_single_video.py data_good_pulls/vid_2_good.mp4")
        print("  python debug_single_video.py data_good_pulls/vid_2_good.mp4 my_debug.mp4")
        sys.exit(1)
    
    video_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    generate_debug_overlay(video_path, output_path)