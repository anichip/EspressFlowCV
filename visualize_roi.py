#!/usr/bin/env python3
"""
Simple script to visualize ROI box on a video frame
"""
import cv2
import os
import glob
from pathlib import Path

# ROI Configuration (from espresso_flow_features.py lines 15-20)
class ROIConfig:
    x0: float = 0.11  
    y0: float = 0.17  
    x1: float = 0.86  
    y1: float = 0.55 

def visualize_roi_on_video(video_path):

    #what do I want it to do. In the frame variable, it should store a frame_num.jpg of my choice. So let's just take the full path pasted from the computer manually, no fancy stuff
    frame = cv2.imread(video_path)
    
    height, width = frame.shape[:2]
    
    # Calculate ROI coordinates
    roi = ROIConfig()
    x0 = int(roi.x0 * width)
    y0 = int(roi.y0 * height) 
    x1 = int(roi.x1 * width)
    y1 = int(roi.y1 * height)
    
    # Draw ROI rectangle (green, thick line)
    cv2.rectangle(frame, (x0, y0), (x1, y1), (0, 255, 0), 3)
    
    # Add text with coordinates
    text = f"ROI: ({roi.x0:.2f}, {roi.y0:.2f}) to ({roi.x1:.2f}, {roi.y1:.2f})"
    cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Resize for display (make smaller)
    # display_frame = cv2.resize(frame, (635, 900))
    
    # Display
    print(f"Video: {os.path.basename(video_path)}")
    print(f"ROI pixel coords: ({x0}, {y0}) to ({x1}, {y1})")
    print("Press any key to close...")
    
    cv2.imshow('ROI Visualization', frame)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":

    video_path = "/Users/r3alistic/Programming/CoffeeCV/frames_good_pulls/vid_47_good/frame_040.jpg"
   
    if os.path.exists(video_path):
        print(f"Using sample video: {video_path[len(video_path)-14:]}")
        visualize_roi_on_video(video_path)
    else:
        print(f"No videos found with pattern: {video_path}")
        print("Please provide a video path:")
        video_path = input().strip()
        if os.path.exists(video_path):
            visualize_roi_on_video(video_path)
        else:
            print("Video not found!")