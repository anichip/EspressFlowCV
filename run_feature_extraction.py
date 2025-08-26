import os
import csv
import pandas as pd
from pathlib import Path
from espresso_flow_features import process_frames_folder, DebugConfig

# --------------------
# CONFIG — edit if needed
# --------------------
class CONFIG:
    FRAMES_GOOD_ROOT = "frames_good_pulls"
    FRAMES_UNDER_ROOT = "frames_under_pulls"
    FPS = 60
    MAX_SECONDS = 7.0
    OUTPUT_CSV = "features_v2.csv"


def _collect_frame_folders(root: Path):
    out = []
    for parent, dirs, files in os.walk(root):
        if any(f.lower().endswith(".jpg") for f in files):
            out.append(Path(parent))
    return sorted(out, key=lambda p: str(p).lower())


def _get_pull_duration(video_folder_path: str, root_folder: str) -> float:
    """
    Extract pull duration from pull_times.csv for a given video folder
    
    Args:
        video_folder_path: Full path to video folder (e.g., "frames_good_pulls/vid_12_good")
        root_folder: Root category folder (e.g., "frames_good_pulls")
    
    Returns:
        Pull duration in seconds, or NaN if not found
    """
    import numpy as np
    
    # Extract video name from path
    video_name = Path(video_folder_path).name  # e.g., "vid_12_good"
    
    # Path to pull_times.csv in the root folder
    pull_times_csv = os.path.join(root_folder, "pull_times.csv")
    
    if not os.path.exists(pull_times_csv):
        print(f"      ⚠️  No pull_times.csv found in {root_folder}")
        return float('nan')
    
    try:
        with open(pull_times_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Clean the video name from CSV (remove file extensions)
                csv_video_name = row["Video_Name"].lower()
                csv_video_name = csv_video_name.replace('.mov', '').replace('.mp4', '').replace('.avi', '')
                
                # Match with folder name
                if csv_video_name == video_name.lower():
                    return float(row["Pull_Duration(s)"])
        
        print(f"      ⚠️  Pull duration not found for {video_name}")
        return float('nan')
        
    except Exception as e:
        print(f"      ⚠️  Error reading pull times: {e}")
        return float('nan')


def main():
    print("🚀 Starting espresso flow feature extraction...")
    print("=" * 60)
    
    # Check for existing CSV and collect processed videos (duplicate-proofing)
    existing_videos = set()
    if os.path.exists(CONFIG.OUTPUT_CSV):
        print(f"📄 Found existing {CONFIG.OUTPUT_CSV}")
        try:
            with open(CONFIG.OUTPUT_CSV, 'r') as existing_file:
                reader = csv.DictReader(existing_file)
                for row in reader:
                    existing_videos.add(row["frame_folder"])
            print(f"⏭️  Skipping {len(existing_videos)} already processed videos")
        except Exception as e:
            print(f"⚠️  Warning: Could not read existing CSV: {e}")
            existing_videos = set()
    
    rows = []
    total_processed = 0
    
    for label, root in [("good", CONFIG.FRAMES_GOOD_ROOT), ("under", CONFIG.FRAMES_UNDER_ROOT)]:
        if not os.path.exists(root):
            print(f"⚠️  Folder {root} not found, skipping...")
            continue
            
        print(f"\n📁 Processing {root}...")
        folders = _collect_frame_folders(Path(root))
        print(f"   Found {len(folders)} video folders")
        
        for folder in folders:
            folder_str = str(folder)
            
            # Skip if already processed
            if folder_str in existing_videos:
                print(f"   ⏭️  Skipping {folder.name} (already processed)")
                continue
                
            print(f"   🎬 Processing {folder.name}...")
            
            try:
                feats = process_frames_folder(folder_str, fps=CONFIG.FPS, max_seconds=CONFIG.MAX_SECONDS, debug=DebugConfig(save_overlay_video=True,save_kymograph=True))
                
                # Add pull duration from pull_times.csv
                pull_duration = _get_pull_duration(folder_str, root)
                feats["pull_duration_s"] = pull_duration
                
                feats["true_label"] = label
                feats["frame_folder"] = folder_str
                rows.append(feats)
                total_processed += 1
                
                # Show pull duration in completion message
                import math
                duration_str = f", Duration: {pull_duration:.1f}s" if not math.isnan(pull_duration) else ""
                print(f"   ✅ {folder.name} complete ({len(feats)} features{duration_str})")
            except Exception as e:
                print(f"   ❌ {folder.name} failed: {e}")
                continue
    
    # Write results
    if rows:
        # Determine if we need to write header (new file vs append)
        write_header = not os.path.exists(CONFIG.OUTPUT_CSV)
        
        # Convert to DataFrame for easy CSV writing
        df_new = pd.DataFrame(rows)
        
        if write_header:
            # New file - write with header
            df_new.to_csv(CONFIG.OUTPUT_CSV, index=False)
            print(f"\n📄 Created new CSV with {len(df_new.columns)} columns")
        else:
            # Append to existing file
            df_new.to_csv(CONFIG.OUTPUT_CSV, mode='a', header=False, index=False)
            print(f"\n📄 Appended to existing CSV")
        
        print(f"🎉 Processing complete!")
        print(f"   📊 {total_processed} new videos processed")
        print(f"   📄 Results saved to: {CONFIG.OUTPUT_CSV}")
    else:
        print("\n⚠️  No new videos to process")


if __name__ == "__main__":
    main()
