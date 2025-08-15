#!/usr/bin/env python3
"""
Test script for new build_features_v2.py functions
Tests each function step by step on real video frames
"""

import os
import sys
sys.path.append('/Users/r3alistic/Programming/CoffeeCV')

from build_features_v2 import *
import cv2
import numpy as np

def test_basic_functions():
    """Test the helper functions first"""
    print("=== Testing Helper Functions ===")
    
    # Test phase division
    phases = divide_frames_into_phases(420)  # 7 seconds @ 60fps
    print(f"✅ Phase division for 420 frames:")
    print(f"   Phase 1 (Hello): frames {phases['phase_1']}")  
    print(f"   Phase 2 (Main Event): frames {phases['phase_2']}")
    print(f"   Phase 3 (Goodbye): frames {phases['phase_3']}")
    
    return True

def debug_frame_with_visualization(frame, frame_name, save_debug=True):
    """
    Debug version of extract_stream_info_from_frame with visualizations
    Shows exactly what the detection algorithm sees
    """
    height, width = frame.shape[:2]
    
    # 1. Create ROI - UPDATED to be wider for different video framings
    roi_x_start =  width // 8          # 12.5% from left (much wider)
    roi_x_end = 15 * width // 16        # 87.5% from left (much wider)       
    roi_y_start = height // 5         # 20% from top         
    roi_y_end = 3 * height // 5       # 60% from top (taller box)                
    
    roi = frame[roi_y_start:roi_y_end, roi_x_start:roi_x_end]
    
    # 2. Color filtering
    hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    lower_espresso = np.array([8, 40, 15])    
    upper_espresso = np.array([30, 255, 180])  
    espresso_mask = cv2.inRange(hsv_roi, lower_espresso, upper_espresso)
    
    # 3. Stream detection
    blurred_mask = cv2.GaussianBlur(espresso_mask, (5, 5), 0)
    contours, _ = cv2.findContours(blurred_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 4. Filter contours and collect info
    valid_contours = []
    roi_center_x = roi.shape[1] // 2
    
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        aspect_ratio = h / w if w > 0 else 0
        contour_center_x = x + w // 2
        distance_from_center = abs(contour_center_x - roi_center_x)
        
        is_valid = (h > 40 and w > 3 and aspect_ratio > 2.0 and 
                   distance_from_center < roi.shape[1] // 3)
        
        valid_contours.append({
            'contour': cnt,
            'bbox': (x, y, w, h),
            'aspect_ratio': aspect_ratio,
            'distance_from_center': distance_from_center,
            'is_valid': is_valid
        })
    
    # Create debug visualization
    if save_debug:
        debug_frame = frame.copy()
        
        # Draw ROI rectangle on original
        cv2.rectangle(debug_frame, (roi_x_start, roi_y_start), (roi_x_end, roi_y_end), (255, 0, 0), 2)
        cv2.putText(debug_frame, "ROI", (roi_x_start, roi_y_start-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        
        # Draw all contours on ROI (shifted coordinates)
        roi_debug = roi.copy()
        for i, cont_info in enumerate(valid_contours):
            x, y, w, h = cont_info['bbox']
            color = (0, 255, 0) if cont_info['is_valid'] else (0, 0, 255)  # Green = valid, Red = invalid
            cv2.rectangle(roi_debug, (x, y), (x+w, y+h), color, 2)
            
            # Add info text
            info_text = f"W:{w} H:{h} AR:{cont_info['aspect_ratio']:.1f}"
            cv2.putText(roi_debug, info_text, (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Save debug images
        cv2.imwrite(f"debug_{frame_name}_original.jpg", debug_frame)
        cv2.imwrite(f"debug_{frame_name}_roi.jpg", roi_debug) 
        cv2.imwrite(f"debug_{frame_name}_mask.jpg", espresso_mask)
        
        print(f"🔍 Debug images saved: debug_{frame_name}_*.jpg")
    
    # Return actual measurements
    hue_mean = np.mean(hsv_roi[:, :, 0])  # Fallback to whole ROI
    brightness_mean = np.mean(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY))
    
    valid_widths = [info['bbox'][2] for info in valid_contours if info['is_valid']]
    stream_width = max(valid_widths) if valid_widths else 0
    
    return hue_mean, brightness_mean, stream_width, len(contours), len(valid_widths)

def test_single_frame_extraction():
    """Test frame extraction on multiple frames with debug visualization"""
    print("\n=== Testing Single Frame Extraction with Debug ===")
    
    # Find a frames folder to test with
    project_root = "/Users/r3alistic/Programming/CoffeeCV"
    test_folders = ["frames_good_pulls", "frames_under_pulls", "frames_over_pulls"]
    
    # Look specifically for the target video. changes from time to time.
    target_video = "vid_75_good"
    test_video_path = None
    
    for folder_name in test_folders:
        folder_path = os.path.join(project_root, folder_name)
        if os.path.exists(folder_path):
            target_path = os.path.join(folder_path, target_video)
            if os.path.exists(target_path) and os.path.isdir(target_path):
                test_video_path = target_path
                print(f"📁 Found target video: {target_video}")
                break
    
    if not test_video_path or not os.path.exists(test_video_path):
        print("❌ No test video found! Make sure you have extracted frames.")
        return False
    
    frames = sorted([f for f in os.listdir(test_video_path) if f.endswith('.jpg')])
    if not frames:
        print("❌ No frames found in video folder")
        return False
    
    print(f"📽️  Found {len(frames)} frames total")
    
    # Test multiple strategic frames
    test_frames = [
        ("early", frames[len(frames)//6]),      # Frame ~17% in (espresso just starting)
        ("middle", frames[len(frames)//2]),     # Frame 50% in (peak extraction) 
        ("late", frames[4*len(frames)//5])      # Frame 80% in (ending phase)
    ]
    
    for phase, frame_name in test_frames:
        frame_path = os.path.join(test_video_path, frame_name)
        frame = cv2.imread(frame_path)
        
        if frame is None:
            print(f"❌ Could not load {phase} frame: {frame_name}")
            continue
            
        print(f"\n🎬 Testing {phase} phase - {frame_name}")
        print(f"📏 Frame size: {frame.shape}")
        
        # Test with debug visualization
        try:
            hue, brightness, width, total_contours, valid_contours = debug_frame_with_visualization(
                frame, f"{phase}_{frame_name.replace('.jpg', '')}")
            
            print(f"✅ Frame analysis results:")
            print(f"   Hue (color): {hue:.2f}")
            print(f"   Brightness: {brightness:.2f}")  
            print(f"   Stream width: {width}")
            print(f"   Total contours found: {total_contours}")
            print(f"   Valid stream contours: {valid_contours}")
            
            if width == 0:
                print("⚠️  Stream width is 0 - check debug images to see what was detected")
            else:
                print("🎉 Stream detected successfully!")
                
        except Exception as e:
            print(f"❌ Frame extraction failed: {e}")
            return False
    
    print(f"\n📸 Debug images saved in: {os.getcwd()}")        
    return True

def test_feature_extraction():
    """Test the timeline feature extraction functions"""
    print("\n=== Testing Feature Extraction Functions ===")
    
    # Create some fake timeline data to test with
    fake_hue_timeline = [15, 18, 20, 22, 25, 27, 30, 32, 35, 38]  # Getting darker over time
    fake_width_timeline = [12, 15, 18, 16, 14, 15, 17, 16, 14, 12]  # Some variation
    fake_brightness_timeline = [125, 123, 120, 118, 115, 112, 110, 108, 105, 102]  # Getting darker (lower brightness)
    
    print(f"🎭 Testing with fake hue timeline: {fake_hue_timeline}")
    print(f"🌊 Testing with fake width timeline: {fake_width_timeline}")
    print(f"💡 Testing with fake brightness timeline: {fake_brightness_timeline}")
    
    # Test Color Journey
    try:
        color_features = extract_color_journey_features(fake_hue_timeline)
        print(f"✅ Color Journey features:")
        for key, value in color_features.items():
            print(f"   {key}: {value}")
    except Exception as e:
        print(f"❌ Color Journey failed: {e}")
        return False
    
    # Test Flow Rhythm  
    try:
        flow_features = extract_flow_rhythm_features(fake_width_timeline)
        print(f"✅ Flow Rhythm features:")
        for key, value in flow_features.items():
            print(f"   {key}: {value}")
    except Exception as e:
        print(f"❌ Flow Rhythm failed: {e}")
        return False
    
    # Test Brightness Momentum (NEW!)
    try:
        brightness_features = extract_brightness_momentum_features(fake_brightness_timeline)
        print(f"✅ Brightness Momentum features:")
        for key, value in brightness_features.items():
            print(f"   {key}: {value}")
        
        # Add interpretation of results
        print("📊 Interpretation:")
        print(f"   momentum {brightness_features['brightness_momentum']:.3f} = average change per frame")
        print(f"   acceleration {brightness_features['brightness_acceleration']:.4f} = smoothness of changes")
        print(f"   trend {brightness_features['brightness_trend']:.2f} = overall direction (negative = getting darker)")
        
    except Exception as e:
        print(f"❌ Brightness Momentum failed: {e}")
        return False
        
    return True

def test_full_video_processing():
    """Test processing a complete video folder"""
    print("\n=== Testing Full Video Processing ===")
    
    # Find first available video folder
    project_root = "/Users/r3alistic/Programming/CoffeeCV"
    test_folders = ["frames_good_pulls", "frames_under_pulls", "frames_over_pulls"]
    
    for folder_name in test_folders:
        folder_path = os.path.join(project_root, folder_name) 
        if os.path.exists(folder_path):
            video_folders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
            if video_folders:
                test_video = video_folders[0]
                test_path = os.path.join(folder_path, test_video)
                print(f"🎬 Testing full processing on: {test_video}")
                
                # Process all frames in this video
                hue_timeline = []
                brightness_timeline = []  
                width_timeline = []
                
                frames = sorted([f for f in os.listdir(test_path) if f.endswith('.jpg')])
                print(f"📽️  Found {len(frames)} frames")
                
                # Process first 20 frames (for speed)
                for i, frame_name in enumerate(frames[:20]):
                    frame_path = os.path.join(test_path, frame_name)
                    frame = cv2.imread(frame_path)
                    if frame is not None:
                        hue, brightness, width = extract_stream_info_from_frame(frame)
                        hue_timeline.append(hue)
                        brightness_timeline.append(brightness)
                        width_timeline.append(width)
                
                print(f"✅ Processed {len(hue_timeline)} frames successfully")
                print(f"📊 Hue range: {min(hue_timeline):.1f} - {max(hue_timeline):.1f}")
                print(f"💡 Brightness range: {min(brightness_timeline):.1f} - {max(brightness_timeline):.1f}")
                print(f"🌊 Width range: {min(width_timeline)} - {max(width_timeline)}")
                
                # Test feature extraction on real data
                color_features = extract_color_journey_features(hue_timeline)
                flow_features = extract_flow_rhythm_features(width_timeline)
                brightness_features = extract_brightness_momentum_features(brightness_timeline)
                
                print(f"🎨 Real Color Journey features: {color_features}")
                print(f"🌊 Real Flow Rhythm features: {flow_features}")
                print(f"💡 Real Brightness Momentum features: {brightness_features}")
                
                return True
    
    print("❌ No video folders found for testing")
    return False

if __name__ == "__main__":
    print("🧪 Testing New Feature Extraction Functions")
    print("=" * 50)
    
    success = True
    success &= test_basic_functions()
    success &= test_single_frame_extraction() 
    success &= test_feature_extraction()
    success &= test_full_video_processing()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed! New functions are working.")
    else:
        print("❌ Some tests failed. Check the output above.")