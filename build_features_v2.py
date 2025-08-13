import os 
import cv2
import csv 
import numpy as np 
import pandas as pd

def divide_frames_into_phases(total_frames):
    """
    Divide frames into 3 phases like a movie: Act 1, Act 2, Act 3
    
    Think of it like a Netflix show:
    - Act 1 (0-33%): The setup - first impressions, how it starts
    - Act 2 (33-66%): The main event - peak action, full extraction
    - Act 3 (66-100%): The resolution - how it ends, final moments
    
    For 420 frames (7 seconds @ 60fps):
    - Phase 1: frames 0-139 (first ~2.3 seconds)
    - Phase 2: frames 140-279 (middle ~2.3 seconds) 
    - Phase 3: frames 280-419 (final ~2.3 seconds)
    """
    
    phase_1_end = total_frames // 3
    phase_2_end = (2 * total_frames) // 3
    
    return {
        'phase_1': (0, phase_1_end),           # The "Hello" phase
        'phase_2': (phase_1_end, phase_2_end), # The "Main Event" phase  
        'phase_3': (phase_2_end, total_frames) # The "Goodbye" phase
    }

def extract_stream_info_from_frame(frame):
    """
    Extract stream characteristics from a single frame using smart detection.
    Returns: (hue_mean, brightness_mean, stream_width)
    
    NEW APPROACH - Much smarter stream detection:
    1. ROI: Only look in center-bottom area (where espresso actually flows)
    2. Color filtering: Target brown/amber colors, not just "dark stuff" 
    3. Shape filtering: Streams are tall & thin, not random blobs
    4. Position consistency: Stream should be vertically oriented in center
    """
    
    height, width = frame.shape[:2]
    
    # 1. REGION OF INTEREST (ROI) - Focus on MIDDLE area where stream flows (not bottom pool!)
    # Like looking through a window at the flowing stream, not the accumulated coffee

    #let us try going even wider
    roi_x_start = width // 8          # Start at 12.5% from left
    roi_x_end = 15 * width // 16     # End at 93.75% from left  
    roi_y_start = height // 5         # Start at 20% from top (maybe a little porta filter area would be nice)
    roi_y_end =  3 * height // 5    # Changed --> End at 60% from top (AVOID bottom accumulation!)
    
    roi = frame[roi_y_start:roi_y_end, roi_x_start:roi_x_end]
    
    # 2. COLOR FILTERING - Look for espresso colors specifically
    hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    
    # Define espresso color ranges in HSV (brown/amber tones)
    # Hue: 10-25 (brown/orange range), Saturation: 50-255, Value: 20-150 (not too bright)
    lower_espresso = np.array([8, 40, 15])    # Lighter brown
    upper_espresso = np.array([30, 255, 180])  # Darker brown
    
    # Create mask for espresso colors
    espresso_mask = cv2.inRange(hsv_roi, lower_espresso, upper_espresso)
    
    # For overall color analysis, use the espresso-colored pixels only
    espresso_pixels = hsv_roi[espresso_mask > 0]
    if len(espresso_pixels) > 0:
        hue_mean = np.mean(espresso_pixels[:, 0])  # Average hue of actual espresso
    else:
        hue_mean = np.mean(hsv_roi[:, :, 0])  # Fallback to whole ROI
    
    # Brightness analysis (on ROI only)
    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    brightness_mean = np.mean(gray_roi)
    
    # 3. STREAM WIDTH DETECTION - Much smarter approach
    # Apply Gaussian blur and use the espresso color mask
    blurred_mask = cv2.GaussianBlur(espresso_mask, (5, 5), 0)
    
    # Find contours in the espresso-colored regions
    contours, _ = cv2.findContours(blurred_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 4. SHAPE & POSITION FILTERING - Only keep stream-like contours
    valid_widths = []
    roi_center_x = roi.shape[1] // 2  # Center of our ROI
    
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        
        # Stream characteristics we expect:
        aspect_ratio = h / w if w > 0 else 0
        contour_center_x = x + w // 2
        distance_from_center = abs(contour_center_x - roi_center_x)
        
        # Filter criteria for a valid espresso stream:
        if (h > 40 and                      # Minimum height (streams are tall)
            w > 3 and                       # Minimum width  
            aspect_ratio > 2.0 and          # Should be taller than wide (vertical stream)
            distance_from_center < roi.shape[1] // 3):  # Should be near center
            valid_widths.append(w)
    
    # Use the widest valid stream (main flow)
    stream_width = max(valid_widths) if valid_widths else 0
    
    return hue_mean, brightness_mean, stream_width

def extract_color_journey_features(hue_timeline):
    """
    FEATURE 1: Color Journey - How does the espresso color change over time?
    
    Real-world analogy: Like watching a sunset
    - Good sunset: starts light → gradually gets deeper → ends rich
    - Bad sunset: stays flat → suddenly dark → or stays too light
    
    Good espresso: light brown → medium brown → rich dark brown
    Under-extracted: stays light brown the whole time
    Over-extracted: goes dark too fast, or gets muddy
    
    Returns 4 features about the color story:
    """
    phases = divide_frames_into_phases(len(hue_timeline))
    
    # Calculate average hue for each phase
    phase1_hue = np.mean(hue_timeline[phases['phase_1'][0]:phases['phase_1'][1]])
    phase2_hue = np.mean(hue_timeline[phases['phase_2'][0]:phases['phase_2'][1]])  
    phase3_hue = np.mean(hue_timeline[phases['phase_3'][0]:phases['phase_3'][1]])
    
    # Feature 1a: Color Progression (phase3 - phase1)
    # Positive = got darker, Negative = got lighter
    color_progression = phase3_hue - phase1_hue
    
    # Feature 1b: Color Consistency (how smooth was the change?)
    # Low variance = smooth change, High variance = erratic
    color_consistency = 1.0 / (1.0 + np.var(hue_timeline))  # Inverted so higher = more consistent
    
    # Feature 1c: Mid-Phase Color Intensity
    # Is the middle phase distinctive? (peak extraction moment)
    mid_phase_intensity = phase2_hue
    
    # Feature 1d: Color Change Rate (how fast did it change?)
    # Like measuring the "speed" of color change
    color_change_rate = abs(color_progression) / len(hue_timeline) if len(hue_timeline) > 0 else 0
    
    return {
        'color_progression': round(color_progression, 3),
        'color_consistency': round(color_consistency, 3),
        'mid_phase_intensity': round(mid_phase_intensity, 3),
        'color_change_rate': round(color_change_rate, 5)
    }

def extract_flow_rhythm_features(width_timeline):
    """
    FEATURE 2: Flow Rhythm - How does the stream width pulse over time?
    
    Real-world analogy: Like monitoring someone's heartbeat on an EKG
    - Healthy heart: steady rhythm, consistent beats, gradual changes
    - Arrhythmia: erratic, sudden spikes, irregular intervals
    
    Good espresso: steady flow, consistent width, smooth rhythm
    Under-extracted: thin, weak flow that might stutter
    Over-extracted: erratic flow, sudden spurts, inconsistent pulsing
    
    Returns 3 features about the flow pattern:
    """
    if not width_timeline or len(width_timeline) < 10:
        return {'flow_steadiness': 0, 'flow_amplitude': 0, 'flow_trend': 0}
    
    phases = divide_frames_into_phases(len(width_timeline))
    
    # Feature 2a: Flow Steadiness (like heart rate variability)
    # Think of it as "How consistent is this person's pulse?"
    # Low variance = steady pulse, High variance = irregular heartbeat
    flow_variance = np.var(width_timeline)
    flow_steadiness = 1.0 / (1.0 + flow_variance)  # Higher = more steady
    
    # Feature 2b: Flow Amplitude (difference between strongest and weakest flow)
    # Like measuring blood pressure: systolic - diastolic
    # "What's the difference between your strongest and weakest pulse?"
    max_width = np.max(width_timeline)
    min_width = np.min(width_timeline)
    flow_amplitude = max_width - min_width
    
    # Feature 2c: Flow Trend (is the stream getting wider or narrower over time?)
    # Like asking "Is your blood pressure rising or falling over the day?"
    # Positive = flow getting stronger/wider, Negative = flow getting weaker/narrower
    phase1_width = np.mean(width_timeline[phases['phase_1'][0]:phases['phase_1'][1]])
    phase3_width = np.mean(width_timeline[phases['phase_3'][0]:phases['phase_3'][1]])
    flow_trend = phase3_width - phase1_width
    
    return {
        'flow_steadiness': round(flow_steadiness, 4),
        'flow_amplitude': round(flow_amplitude, 2),
        'flow_trend': round(flow_trend, 2)
    }

print("✅ Feature 2 (Flow Rhythm) implemented!")

"""
=== NEXT STEPS TO COMPLETE THE NEW FEATURE EXTRACTION SYSTEM ===

STATUS: 2 out of 5 dynamic features completed and tested

REMAINING FEATURES TO IMPLEMENT:

3. **Brightness Momentum** (3 sub-features):
   - How fast brightness changes over time (like acceleration/deceleration)
   - Phase-to-phase brightness transitions
   - Overall brightness trend direction
   
4. **Stream Consistency Score** (2 sub-features):  
   - Overall "steadiness" combining color + width + brightness
   - Consistency across all three phases (how uniform is the extraction?)
   
5. **Phase Transitions** (3 sub-features):
   - Smoothness of transition from phase 1 → 2
   - Smoothness of transition from phase 2 → 3  
   - Overall transition quality score

INTEGRATION STEPS NEEDED:
1. Add remaining 3 feature extraction functions above
2. Create main processing loop (similar to original build_features.py):
   - Loop through frame folders (frames_good_pulls, frames_under_pulls, frames_over_pulls)
   - Process each video folder to create timelines (hue_timeline, width_timeline, brightness_timeline)
   - Extract all 5 dynamic feature sets per video
   - Write to enhanced features_v2.csv with 15+ columns instead of 5
3. Test on full dataset
4. Compare new temporal features vs old static features in ML models

FINAL OUTPUT: features_v2.csv with columns like:
- Video_Name, Category, Pull_Duration
- color_progression, color_consistency, mid_phase_intensity, color_change_rate  
- flow_steadiness, flow_amplitude, flow_trend
- brightness_momentum, brightness_acceleration, brightness_trend
- stream_consistency, phase_uniformity
- transition_1_2, transition_2_3, overall_transition_quality

This approach should capture the "story" of espresso extraction much better than simple averages!
"""