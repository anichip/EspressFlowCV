import os 
import cv2
import csv 
import numpy as np 
import pandas as pd

#What are the featues we want to extract
# - pull duration (from csv)
# - flow variance (smoothness)
# - brightness_mean 
# - mean_hue (color of the stream)
# - stream_width_avg 

project_root = "/Users/r3alistic/Programming/CoffeeCV"
csv_output_path = os.path.join(project_root, "features.csv")

frame_folders_root = [
    "frames_perfect_pulls",
    "frames_mid_pulls",
    "frames_under_pulls",
    "frames_over_pulls"
]

# Check if CSV already exists and collect existing video names
existing_videos = set()
if os.path.exists(csv_output_path): # checks “Hey, has this CSV file already been created?”

    #if the file exists, it opens it in read mode
    # with...as... is for safely opening a file. And we are storign it in variable existing_file
    with open(csv_output_path, 'r') as existing_file:
        reader = csv.DictReader(existing_file) #each row is a dictionary
        for row in reader:
            existing_videos.add(row["Video_Name"])

#so that just populated existing_videos with stuff that is already in feature.csv, if feature.csv exists

#Loop through all folders
feature_data = []

for folder_name in frame_folders_root:
    #so for every vid folder in the folder for the frames of the 4 categories
    folder_path = os.path.join(project_root,folder_name)

    #so here we have the frames_{category}_pulls full path under folder_path
    #need to access the path of the pull times, turn it into a data frame
    pull_path = os.path.join(folder_path,"pull_times.csv")
    df_pull = pd.read_csv(pull_path)

    #now in those folders, go through each one and join the path
    for video_folder in os.listdir(folder_path):

        #repeat prevention
        if video_folder in existing_videos:
            print(f"⏭️ Skipping {video_folder} (already in CSV)")
            continue

        video_folder_path = os.path.join(folder_path,video_folder)

        #we need to make sure it is one of those folders and not the pull_times.csv
        #GOOD CATCH ANI!
        if not os.path.isdir(video_folder_path):
            #not a folder
            continue

        #no directory was made. This was already made.

        #we still in the for loop. video_folder_path is to one of the vid_{number}_{category} files with hundreds of frames in it

        all_hue_values = [] # stores hue (color) so that we can later take the average
        all_brightness_values = [] # stores grayscale brightness

        for frame_name in sorted(os.listdir(video_folder_path)):   # loop over all images
            frame_path = os.path.join(video_folder_path, frame_name)

            # just frame, not ret, frame because this is just cv2 and not cv2.VideoCapture
            # we are analyzing the frame now. 
            frame = cv2.imread(frame_path)
            if frame is None:
                continue

            # Convert from the default BGR to HSV for color analysis
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            hue = hsv[:, :, 0]  # Extract hue channel (0-180)
            all_hue_values.append(np.mean(hue)) #across all pixels in this one frame, take the mean and add it 

            #conver to Grayscale to analzye brightness 
            gray = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
            all_brightness_values.append(np.mean(gray))

        #NOW THE FRAME LOOP HAS ENDED AND WE ARE ABOUT TO MOVE TO THE NEXT vid_{number}_{category} FOLDER
        #for that folder though, let's calculate the average hue and brightness for real. 
        # This is now for That VIDEO SPECIFICALLY
        avg_hue = np.mean(all_hue_values)
        avg_brightness = np.mean(all_brightness_values)

        match = df_pull[df_pull["Video_Name"] == video_folder]
        if not match.empty:
            pull_duration = match.iloc[0]["Pull_Duration(s)"]
        else:
            print(f"⚠️ No pull duration found for {video_folder}, setting to None")
            pull_duration = None

        #now store the data we just calculated. 
        #feature_data is a list, but every entry will be a row
        # that row has a name (vid_{number}_{category} FOLDER) , a category , avg_hue, and avg_brightness
        feature_data.append([
            video_folder, 
            folder_name.replace("frames_", "").replace("_pulls", ""),  #ex:  'perfect'
            round(avg_hue,2),
            round(avg_brightness,2),
            pull_duration
        ])

# Append new data to CSV
write_header = not os.path.exists(csv_output_path)
with open(csv_output_path, 'a', newline='') as csvfile:
    writer = csv.writer(csvfile)
    if write_header:
        writer.writerow(["Video_Name", "Category", "Avg_Hue", "Avg_Brightness","Pull_Duration"])
    writer.writerows(feature_data)

print(f"✅ Feature extraction complete. {len(feature_data)} new rows added.")


# Still need to do flow_variance and stream_width, but this is good progress for today