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
    1. ROI: Only look in center-mid-top area (where espresso actually flows)
    2. Color filtering: Target brown/amber colors, not just "dark stuff" 
    3. Shape filtering: Streams are tall & thin, not random brown blobs
    4. Position consistency: Stream should be vertically oriented in center
    """
    
    height, width = frame.shape[:2]
    
    # 1. REGION OF INTEREST (ROI) - OPTIMIZED for reliable stream capture across all mug heights
    # Strategy: Wide capture (portafilter to container top) based on "container always directly under"
    
    # {[[This is fairly easy to understand. We're telling the computer to only look here for coffee streams]]}
    
    # ENHANCED WIDE ROI - Captures streams from portafilter to container rim reliably
    roi_x_start = width // 9         # Start at 11% from left (wider than 12.5%)
    roi_x_end = 9 * width // 10      # End at 90% from left (wider than 93.75%)
    roi_y_start = height // 7         # Start at 14% from top (higher to catch portafilter area) 
    roi_y_end = height // 2     # End at 70% from top (deeper to catch short mugs, avoid bottom pool)
    
    roi = frame[roi_y_start:roi_y_end, roi_x_start:roi_x_end]
    
    # 2. EDGE-BASED DETECTION - More robust than color filtering
    # Convert to grayscale for edge detection
    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    blurred_gray = cv2.GaussianBlur(gray_roi, (5, 5), 0)
    
    # Edge detection with Canny
    edges = cv2.Canny(blurred_gray, 50, 150)
    
    # For color analysis, use HSV on the ROI (independent of stream detection)
    hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    hue_mean = np.mean(hsv_roi[:, :, 0])  # Simple average hue of ROI
    
    # Brightness analysis (on ROI only)  
    brightness_mean = np.mean(gray_roi)
    
    # 3. STREAM WIDTH DETECTION - Edge-based approach
    
    # Find contours from edge detection
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 4. SHAPE & POSITION FILTERING - Only keep stream-like contours
    valid_widths = []
    roi_center_x = roi.shape[1] // 2  # Center of our ROI
    
    #we want to filter for stream shapes only
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        
        # Stream characteristics we expect:
        aspect_ratio = h / w if w > 0 else 0
        contour_center_x = x + w // 2
        distance_from_center = abs(contour_center_x - roi_center_x)
        
        # EDGE-BASED Filter criteria for espresso streams - optimized for edge contours!
        area = cv2.contourArea(cnt)
        if (h > 30 and                      # Minimum height for streams
            w > 2 and                       # Allow thin streams 
            aspect_ratio > 2.0 and          # More vertical than horizontal
            area > 100):                    # Minimum area to filter noise

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
    flow_steadiness = 1.0 / (1.0 + flow_variance)  # Higher = more steady because inverted.
    
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

def extract_brightness_momentum_features(brightness_timeline):
    """
    FEATURE 3: Brightness Momentum - How fast does brightness change over time?
    
    INPUT: brightness_timeline 
    - What it is: Array of brightness values (one per frame) from extract_stream_info_from_frame()
    - Example: [120.5, 118.2, 115.8, 112.1, ...] for 420 frames
    - Status: ❌ NOT YET CREATED - we need to build this timeline in main processing loop
    - How to create: For each frame, take brightness_mean from extract_stream_info_from_frame()
    
    Real-world analogy: Like measuring how fast a car accelerates/decelerates
    - Sports car: smooth acceleration → steady speed → gentle braking
    - Broken car: jerky acceleration → sudden stops → erratic speed changes
    
    Good espresso: gradual brightness changes (smooth extraction)
    Under-extracted: brightness drops too slowly (weak extraction)
    Over-extracted: brightness drops too fast (harsh extraction)
    
    Returns 3 features about brightness momentum:
    """
    if not brightness_timeline or len(brightness_timeline) < 10:
        return {'brightness_momentum': 0, 'brightness_acceleration': 0, 'brightness_trend': 0}
    
    phases = divide_frames_into_phases(len(brightness_timeline))
    
    # Feature 3a: Brightness Momentum (overall "speed" of brightness change)
    # Like measuring the average speed of a car over a trip
    # Calculate frame-to-frame brightness changes (derivatives)
    brightness_changes = []
    for i in range(1, len(brightness_timeline)):
        change = abs(brightness_timeline[i] - brightness_timeline[i-1])
        brightness_changes.append(change)
    
    brightness_momentum = np.mean(brightness_changes) if brightness_changes else 0
    
    # Feature 3b: Brightness Acceleration (is the rate of change speeding up or slowing down?)
    # Like measuring if a car is accelerating or decelerating
    # Calculate second derivative (change of change)
    accelerations = []
    for i in range(2, len(brightness_timeline)):
        # Compare consecutive changes to see if rate is increasing/decreasing
        change1 = brightness_timeline[i-1] - brightness_timeline[i-2]
        change2 = brightness_timeline[i] - brightness_timeline[i-1]
        acceleration = abs(change2 - change1)
        accelerations.append(acceleration)
    
    brightness_acceleration = np.mean(accelerations) if accelerations else 0
    
    # Feature 3c: Brightness Trend (overall direction: getting brighter or darker?)
    # Like asking "Did you end up going uphill or downhill overall?"
    # Positive = getting brighter, Negative = getting darker
    phase1_brightness = np.mean(brightness_timeline[phases['phase_1'][0]:phases['phase_1'][1]])
    phase3_brightness = np.mean(brightness_timeline[phases['phase_3'][0]:phases['phase_3'][1]])
    brightness_trend = phase3_brightness - phase1_brightness
    
    return {
        'brightness_momentum': round(brightness_momentum, 3),
        'brightness_acceleration': round(brightness_acceleration, 4),
        'brightness_trend': round(brightness_trend, 2)
    }

def extract_stream_consistency_features(hue_timeline, brightness_timeline, width_timeline):
    """
    FEATURE 4: Stream Consistency Score - How "steady" is the overall extraction?
    
    INPUTS: 
    - hue_timeline: ✅ HAVE from extract_stream_info_from_frame()
    - brightness_timeline: ✅ HAVE from extract_stream_info_from_frame()  
    - width_timeline: ✅ HAVE from extract_stream_info_from_frame()
    - Status: ❌ NOT YET CREATED - we need to build these timelines in main processing loop
    - How to create: For each frame, collect all 3 values into separate arrays
    
    Real-world analogy: Like rating a chef's consistency
    - Master chef: consistent knife cuts, steady heat, uniform cooking
    - Amateur chef: uneven cuts, temperature fluctuations, inconsistent results
    
    Good espresso: consistent color changes + steady flow + smooth brightness
    Under-extracted: inconsistent (stops/starts, color jumps, erratic flow)
    Over-extracted: chaotic (wild variations, unstable extraction)
    
    Returns 2 features about overall extraction steadiness:
    """
    # Handle edge cases
    if (not hue_timeline or not brightness_timeline or not width_timeline or
        len(hue_timeline) < 10 or len(brightness_timeline) < 10 or len(width_timeline) < 10):
        return {'overall_steadiness': 0, 'phase_uniformity': 0}
    
    # Ensure all timelines are same length (they should be)
    min_length = min(len(hue_timeline), len(brightness_timeline), len(width_timeline))
    hue_timeline = hue_timeline[:min_length]
    brightness_timeline = brightness_timeline[:min_length]
    width_timeline = width_timeline[:min_length]
    
    phases = divide_frames_into_phases(min_length)
    
    # Feature 4a: Overall Steadiness (combine consistency across all 3 measurements)
    # Like asking "How consistent is this chef across all cooking skills?"
    
    # Calculate individual consistencies (using coefficient of variation = std/mean)
    def calculate_consistency(timeline):
        if len(timeline) == 0 or np.mean(timeline) == 0:
            return 0
        cv = np.std(timeline) / np.mean(timeline)  # Lower CV (coefficient of variation) = more consistent
        return 1.0 / (1.0 + cv)  # Invert so higher = more consistent
    
    hue_consistency = calculate_consistency(hue_timeline)
    brightness_consistency = calculate_consistency(brightness_timeline)  
    width_consistency = calculate_consistency(width_timeline)
    
    # __> Overall steadiness is the harmonic mean of all three consistencies
    # (harmonic mean punishes outliers more than arithmetic mean)

    #this is one of the things we RETURN
    overall_steadiness = 3.0 / (1.0/hue_consistency + 1.0/brightness_consistency + 1.0/width_consistency) if all([hue_consistency, brightness_consistency, width_consistency]) else 0
    
    # Feature 4b: Phase Uniformity (how similar are the 3 phases to each other?)
    # Like asking "Does this chef cook consistently from appetizer to dessert?"
    
    def get_phase_stats(timeline, phases):
        phase1_mean = np.mean(timeline[phases['phase_1'][0]:phases['phase_1'][1]])
        phase2_mean = np.mean(timeline[phases['phase_2'][0]:phases['phase_2'][1]])
        phase3_mean = np.mean(timeline[phases['phase_3'][0]:phases['phase_3'][1]])
        return [phase1_mean, phase2_mean, phase3_mean]
    
    hue_phases = get_phase_stats(hue_timeline, phases)
    brightness_phases = get_phase_stats(brightness_timeline, phases)
    width_phases = get_phase_stats(width_timeline, phases)
    
    # Calculate how uniform each measurement is across phases (lower variance = more uniform)
    hue_uniformity = 1.0 / (1.0 + np.var(hue_phases))
    brightness_uniformity = 1.0 / (1.0 + np.var(brightness_phases))
    width_uniformity = 1.0 / (1.0 + np.var(width_phases))
    
    # Phase uniformity is average of all three uniformities
    #the second thing we RETURN 
    phase_uniformity = (hue_uniformity + brightness_uniformity + width_uniformity) / 3.0

    # phase means --> variance of the phases --> average of the variances = phase uniformity
    
    return {
        'overall_steadiness': round(overall_steadiness, 4),
        'phase_uniformity': round(phase_uniformity, 4)
    }



def extract_phase_transition_features(hue_timeline, brightness_timeline, width_timeline):
    """
    FEATURE 5: Phase Transitions - How smoothly does extraction transition between phases?
    
    INPUTS: 
    - hue_timeline: ✅ HAVE from extract_stream_info_from_frame()
    - brightness_timeline: ✅ HAVE from extract_stream_info_from_frame()  
    - width_timeline: ✅ HAVE from extract_stream_info_from_frame()
    - Status: ❌ NOT YET CREATED - we need to build these timelines in main processing loop
    - How to create: For each frame, collect all 3 values into separate arrays
    
    Real-world analogy: Like judging a dancer's transitions between moves
    - Professional dancer: smooth transitions, graceful flow between poses
    - Amateur dancer: jerky movements, abrupt changes, choppy transitions
    
    Good espresso: smooth phase transitions (gradual color/flow changes)
    Under-extracted: abrupt stops/starts between phases
    Over-extracted: chaotic transitions, sudden changes
    
    Returns 3 features about phase-to-phase smoothness:
    """
    # Handle edge cases
    if (not hue_timeline or not brightness_timeline or not width_timeline or
        len(hue_timeline) < 30):  # Need enough frames to analyze transitions
        return {'transition_1_2_smoothness': 0, 'transition_2_3_smoothness': 0, 'overall_transition_quality': 0}
    
    # Ensure all timelines are same length
    min_length = min(len(hue_timeline), len(brightness_timeline), len(width_timeline))
    hue_timeline = hue_timeline[:min_length]
    brightness_timeline = brightness_timeline[:min_length]
    width_timeline = width_timeline[:min_length]
    
    phases = divide_frames_into_phases(min_length)
    
    def calculate_transition_smoothness(timeline, start_phase_end, end_phase_start, transition_window=10):
        """
        Calculate how smooth a transition is between two phases
        
        We look at frames around the phase boundary:
        - Before transition: frames [boundary-window : boundary]
        - After transition: frames [boundary : boundary+window]
        - Smooth = similar slopes on both sides
        """
        # Get transition window around the phase boundary
        boundary = start_phase_end
        before_start = max(0, boundary - transition_window)
        after_end = min(len(timeline), boundary + transition_window)
        
        before_transition = timeline[before_start:boundary]
        after_transition = timeline[boundary:after_end]
        
        if len(before_transition) < 3 or len(after_transition) < 3:
            return 0
        
        # Calculate slopes (rate of change) before and after transition
        def calculate_slope(data):
            if len(data) < 2:
                return 0
            # Linear regression slope: how fast is data changing?
            x = np.arange(len(data))
            slope = np.polyfit(x, data, 1)[0] if len(data) > 1 else 0
            return slope
        
        before_slope = calculate_slope(before_transition)
        after_slope = calculate_slope(after_transition)
        
        # Smooth transition = similar slopes (small difference)
        slope_difference = abs(before_slope - after_slope)
        smoothness = 1.0 / (1.0 + slope_difference)  # Higher = smoother
        
        return smoothness
    
    # Feature 5a: Phase 1→2 Transition Smoothness
    # How smoothly does "hello" phase transition to "main event" phase?
    hue_trans_1_2 = calculate_transition_smoothness(hue_timeline, phases['phase_1'][1], phases['phase_2'][0])
    brightness_trans_1_2 = calculate_transition_smoothness(brightness_timeline, phases['phase_1'][1], phases['phase_2'][0])
    width_trans_1_2 = calculate_transition_smoothness(width_timeline, phases['phase_1'][1], phases['phase_2'][0])
    
    transition_1_2_smoothness = (hue_trans_1_2 + brightness_trans_1_2 + width_trans_1_2) / 3.0
    
    # Feature 5b: Phase 2→3 Transition Smoothness  
    # How smoothly does "main event" phase transition to "goodbye" phase?
    hue_trans_2_3 = calculate_transition_smoothness(hue_timeline, phases['phase_2'][1], phases['phase_3'][0])
    brightness_trans_2_3 = calculate_transition_smoothness(brightness_timeline, phases['phase_2'][1], phases['phase_3'][0])
    width_trans_2_3 = calculate_transition_smoothness(width_timeline, phases['phase_2'][1], phases['phase_3'][0])
    
    transition_2_3_smoothness = (hue_trans_2_3 + brightness_trans_2_3 + width_trans_2_3) / 3.0
    
    # Feature 5c: Overall Transition Quality
    # How good are the transitions overall? (average of both transitions)
    overall_transition_quality = (transition_1_2_smoothness + transition_2_3_smoothness) / 2.0
    
    return {
        'transition_1_2_smoothness': round(transition_1_2_smoothness, 4),
        'transition_2_3_smoothness': round(transition_2_3_smoothness, 4), 
        'overall_transition_quality': round(overall_transition_quality, 4)
    }

print("✅ Feature 5 (Phase Transitions) implemented!")
print("🎉 All 5 dynamic features complete! Ready for integration.")

"""
=== NEXT STEPS TO COMPLETE THE NEW FEATURE EXTRACTION SYSTEM ===

STATUS: ✅ ALL 5 DYNAMIC FEATURES IMPLEMENTED AND READY FOR INTEGRATION!

COMPLETED FEATURES:

1. **Color Journey** (4 sub-features): ✅ DONE
   - color_progression, color_consistency, mid_phase_intensity, color_change_rate
   
2. **Flow Rhythm** (3 sub-features): ✅ DONE
   - flow_steadiness, flow_amplitude, flow_trend
   
3. **Brightness Momentum** (3 sub-features): ✅ DONE
   - brightness_momentum, brightness_acceleration, brightness_trend
   
4. **Stream Consistency Score** (2 sub-features): ✅ DONE  
   - overall_steadiness, phase_uniformity
   
5. **Phase Transitions** (3 sub-features): ✅ DONE
   - transition_1_2_smoothness, transition_2_3_smoothness, overall_transition_quality

INTEGRATION STEPS NEEDED:
1. ✅ All feature extraction functions implemented
2. 🔄 NEXT: Create main processing loop (similar to original build_features.py):
   - Loop through frame folders (frames_good_pulls, frames_under_pulls, frames_over_pulls)
   - Process each video folder to create timelines (hue_timeline, width_timeline, brightness_timeline)
   - Extract all 5 dynamic feature sets per video
   - Write to enhanced features_v2.csv with 15+ columns instead of 5
3. Test on full dataset  
4. Compare new temporal features vs old static features in ML models

FINAL OUTPUT: features_v2.csv with columns like:
- Video_Name, Category, Pull_Duration (3 basic columns)
- color_progression, color_consistency, mid_phase_intensity, color_change_rate (4 color features)
- flow_steadiness, flow_amplitude, flow_trend (3 flow features)
- brightness_momentum, brightness_acceleration, brightness_trend (3 brightness features)
- overall_steadiness, phase_uniformity (2 consistency features)
- transition_1_2_smoothness, transition_2_3_smoothness, overall_transition_quality (3 transition features)

TOTAL: 18 features capturing the complete temporal "story" of espresso extraction!
"""

# ===== MAIN PROCESSING LOOP =====

def process_all_videos():
    """
    Main function to process all videos and create features_v2.csv
    
    This replaces the simple averaging approach with comprehensive temporal analysis
    """
    
    print("🚀 Starting temporal feature extraction...")
    print("=" * 60)
    
    # Configuration
    project_root = "/Users/r3alistic/Programming/CoffeeCV"
    csv_output_path = os.path.join(project_root, "features_v2.csv")
    
    frame_folders = [
        "frames_good_pulls",
        "frames_under_pulls"
    ]
    
    # Check for existing CSV and collect processed videos
    existing_videos = set()
    if os.path.exists(csv_output_path):
        print(f"📄 Found existing {csv_output_path}")
        with open(csv_output_path, 'r') as existing_file:
            reader = csv.DictReader(existing_file)
            for row in reader:
                existing_videos.add(row["Video_Name"])
        print(f"⏭️  Skipping {len(existing_videos)} already processed videos")
    
    # Main processing
    all_feature_data = []
    total_processed = 0
    
    for folder_name in frame_folders:
        folder_path = os.path.join(project_root, folder_name)

        if not os.path.exists(folder_path):
            print(f"⚠️  Folder {folder_name} not found, skipping...")
            continue
            
        print(f"\n📁 Processing {folder_name}...")
        category = folder_name.replace("frames_", "").replace("_pulls", "")
        
        # Process each video in this category
        #this already checks if it is a folder of video frames. 
        video_folders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
        print(f"   Found {len(video_folders)} videos in {folder_name}")
        
        for video_folder in video_folders:
            if video_folder in existing_videos:
                print(f"   ⏭️  Skipping {video_folder} (already processed)")
                continue
                
            print(f"   🎬 Processing {video_folder}...")
            
            # Process this individual video
            video_features = process_single_video(folder_path, video_folder, category)
            
            if video_features:
                all_feature_data.append(video_features)
                total_processed += 1
                print(f"   ✅ {video_folder} complete ({len(video_features)} features)")
            else:
                print(f"   ❌ {video_folder} failed")
    
    # Write results
    if all_feature_data:
        write_features_to_csv(all_feature_data, csv_output_path)
        print(f"\n🎉 Processing complete!")
        print(f"   📊 {total_processed} new videos processed")
        print(f"   📄 Results saved to: {csv_output_path}")
    else:
        print("\n⚠️  No new videos to process")
        
    return csv_output_path

def process_single_video(folder_path, video_folder, category):
    """
    Process a single video folder to extract all temporal features
    
    This is where the magic happens - we build the 3 timelines and extract 18 features!
    """
    
    video_path = os.path.join(folder_path, video_folder)
    
    # Get pull duration from the metadata CSV
    pull_times_csv = os.path.join(folder_path, "pull_times.csv")
    pull_duration = get_pull_duration(pull_times_csv, video_folder)
    
    # Build the three timelines by processing all frames
    hue_timeline = []
    brightness_timeline = []
    width_timeline = []
    
    # Get all frame files
    frame_files = sorted([f for f in os.listdir(video_path) if f.endswith('.jpg')])
    
    if len(frame_files) < 30:  # Need minimum frames for temporal analysis
        print(f"      ⚠️  Only {len(frame_files)} frames found, skipping...")
        return None
    
    print(f"      📽️  Processing {len(frame_files)} frames...")
    
    # Process each frame to build timelines
    frames_processed = 0
    for frame_file in frame_files:
        frame_path = os.path.join(video_path, frame_file)
        frame = cv2.imread(frame_path)
        
        if frame is not None:
            try:
                hue, brightness, width = extract_stream_info_from_frame(frame)
                hue_timeline.append(hue)
                brightness_timeline.append(brightness)
                width_timeline.append(width)
                frames_processed += 1
            except Exception as e:
                print(f"      ⚠️  Error processing {frame_file}: {e}")
                continue
    
    if frames_processed < 30:
        print(f"      ❌ Only {frames_processed} frames processed successfully, skipping...")
        return None
    
    print(f"      ✅ Successfully processed {frames_processed} frames")
    
    # Extract all 5 feature sets from the timelines
    try:
        color_features = extract_color_journey_features(hue_timeline)
        flow_features = extract_flow_rhythm_features(width_timeline)
        brightness_features = extract_brightness_momentum_features(brightness_timeline)
        consistency_features = extract_stream_consistency_features(hue_timeline, brightness_timeline, width_timeline)
        transition_features = extract_phase_transition_features(hue_timeline, brightness_timeline, width_timeline)
        
        # Combine all features into one dictionary
        all_features = {
            'Video_Name': video_folder,
            'Category': category,
            'Pull_Duration': pull_duration,
            'Frames_Processed': frames_processed
        }
        
        # Add all feature sets
        all_features.update(color_features)      # 4 features
        all_features.update(flow_features)       # 3 features  
        all_features.update(brightness_features) # 3 features
        all_features.update(consistency_features) # 2 features
        all_features.update(transition_features)  # 3 features
        
        print(f"      🎯 Extracted {len(all_features)-4} temporal features")  # -4 for metadata
        return all_features
        
    except Exception as e:
        print(f"      ❌ Feature extraction failed: {e}")
        return None

def get_pull_duration(pull_times_csv, video_folder):
    """
    Get pull duration for a video from the pull_times.csv file
    """
    try:
        if os.path.exists(pull_times_csv):
            df_pull = pd.read_csv(pull_times_csv)
            # Clean video names for matching (remove file extensions)
            df_pull["Video_Name"] = df_pull["Video_Name"].str.lower().str.replace(r"\.(mov|mp4|avi)$", "", regex=True)
            
            # Find matching video
            match = df_pull[df_pull["Video_Name"] == video_folder.lower()]
            if not match.empty:
                return match.iloc[0]["Pull_Duration(s)"]
        
        print(f"      ⚠️  Pull duration not found for {video_folder}")
        return np.nan
        
    except Exception as e:
        print(f"      ⚠️  Error reading pull times: {e}")
        return np.nan

def write_features_to_csv(all_feature_data, csv_output_path):
    """
    Write all extracted features to CSV file
    
    Creates a comprehensive CSV with 22 columns (4 metadata + 18 temporal features)
    """
    
    if not all_feature_data:
        print("⚠️  No feature data to write")
        return
        
    # Define column order for consistent CSV structure
    columns = [
        # Metadata (4 columns)
        'Video_Name', 'Category', 'Pull_Duration', 'Frames_Processed',
        
        # Color Journey features (4 columns)  
        'color_progression', 'color_consistency', 'mid_phase_intensity', 'color_change_rate',
        
        # Flow Rhythm features (3 columns)
        'flow_steadiness', 'flow_amplitude', 'flow_trend',
        
        # Brightness Momentum features (3 columns)
        'brightness_momentum', 'brightness_acceleration', 'brightness_trend',
        
        # Stream Consistency features (2 columns)
        'overall_steadiness', 'phase_uniformity',
        
        # Phase Transition features (3 columns)
        'transition_1_2_smoothness', 'transition_2_3_smoothness', 'overall_transition_quality'
    ]
    
    # Check if file exists to determine if we need header
    write_header = not os.path.exists(csv_output_path)
    
    # Write to CSV
    try:
        with open(csv_output_path, 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=columns)
            
            if write_header:
                writer.writeheader()
                print(f"📄 Created new CSV with {len(columns)} columns")
            
            # Write all feature data
            for features in all_feature_data:
                writer.writerow(features)
                
        print(f"✅ Successfully wrote {len(all_feature_data)} rows to {csv_output_path}")
        
    except Exception as e:
        print(f"❌ Error writing to CSV: {e}")

if __name__ == "__main__":
    # Run the main processing when script is executed directly
    output_file = process_all_videos()
    print(f"\n✅ Temporal feature extraction complete: {output_file}")