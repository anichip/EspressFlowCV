import os 
import cv2
import csv

def run_extraction(category):

    #User settings 
    #choose the folder where the extracted frames should go 

    #Now switched to 11 seconds at 30 fps, so each vid will standardize to 330 frames

    input_folder = f"/Users/r3alistic/Programming/CoffeeCV/data_{category}_pulls"
    output_root = f"/Users/r3alistic/Programming/CoffeeCV/frames_{category}_pulls"
    clip_duration_sec = 7
    target_fps = 60
    pull_data = []

    #create output directory for the frames
    os.makedirs(output_root, exist_ok=True)

    # Function to check if video has already been processed
    def is_video_processed(video_name, csv_path, output_root):
        # Check if frames directory exists
        video_basename = os.path.splitext(video_name)[0]
        output_dir = os.path.join(output_root, video_basename)
        
        if not os.path.exists(output_dir):
            return False
        
        # Check if CSV exists and contains this video
        if os.path.exists(csv_path):
            try:
                with open(csv_path, 'r', newline='') as csvfile:
                    reader = csv.reader(csvfile)
                    next(reader, None)  # Skip header
                    for row in reader:
                        if row and row[0] == video_name:
                            return True
            except:
                pass  # If CSV reading fails, assume not processed
        
        return False

    # Get CSV path early to use in duplicate check
    csv_path = os.path.join(output_root, "pull_times.csv")

    #Loop through each video in the input folder
    for video_name in os.listdir(input_folder):

        #skip through it if it is not a video 
        if not video_name.lower().endswith(('.mp4', '.mov', '.avi')):
            continue 
        
        # Check if video has already been processed
        if is_video_processed(video_name, csv_path, output_root):
            print(f"⏭️  Skipping {video_name} - already processed")
            continue
        
        # Create the full file path to the video
        video_path = os.path.join(input_folder, video_name)
        
        #use OpenCV to open the video 
        cap = cv2.VideoCapture(video_path)

        #Sanity check: if it fails to open the video, then skip it
        if not cap.isOpened():
            print(f"⚠️ Couldn't open {video_name}")
            continue  
        
        #extract video frame rate (fps--> frames per second)
        fps = cap.get(cv2.CAP_PROP_FPS)

        # Get total number of frames in the video
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))  

        #to get the original uncropped pull duration 
        pull_duration = round(total_frames / fps,2)

        print(f"📹 Processing {video_name} | FPS: {fps} | Total Frames: {total_frames}")

        #How many frames to save? max 11 seconds, so max 330 frames
        #so this solves my dilemma of what to do if the video was too short: 
        # the choice is whichever has smaller amount of frames total: the threshold or the video
        max_frames = int(min(clip_duration_sec*target_fps,total_frames))

        # Remove file extension to use as folder name
        #so vid_1_perfect.mov will now split into vid_1_perfect and .mov
        #and then video basename is vid_1_perfect
        video_basename = os.path.splitext(video_name)[0]  


        output_dir = os.path.join(output_root,video_basename)

        os.makedirs(output_dir,exist_ok=True)


        ########### part 2: saving those crucial first 7 seconds (skipping first 1 second)
        frame_count = 0 
        saved_frame_count = 0
        last_valid_frame=None
        
        # Skip the first 1 second to avoid empty frames before espresso flow starts
        frames_to_skip = int(fps)  # Skip 1 second worth of frames
        
        #while that video we opened is valid, and we still have not reached the end of the video
        while cap.isOpened() and saved_frame_count < max_frames:
            #I think ret is if the frame is there and read, and frame is the frame itself
            ret, frame = cap.read()
            if not ret:
                break #reached end of vid 
                #we will get here if ret==False, which means they ain't get that frame

            # Skip frames from the first second to avoid empty frames before flow starts
            if frame_count < frames_to_skip:
                frame_count += 1
                continue

            #Let me tell you why this works:
            #so we are still in the while loop
            #if the frame is good, then I am going to copy it in case it's the last good frame right before ret becomes False
            #but see that imwrite on line 82 works with frame because it's valid inside that if 
            #the second one won't be because the while loop is done for
            #so then we will save last_valid_frame for padding

            if frame is not None:

                last_valid_frame = frame.copy()
                #still in the while loop
                #save one frame per frame 
                frame_filename = os.path.join(output_dir,f"frame_{saved_frame_count:03d}.jpg")
                #saving the frame under the name frame_filename wow that was neat
                cv2.imwrite(frame_filename,frame)

                #increment to get to the next frame
                saved_frame_count+=1

            frame_count+=1

        #outside while loop. still in the video_name's for loop though

        #Pad short videos with the last frame until 390 frames are saved,
        #which is how we deal with shorter videos
        if saved_frame_count < max_frames and last_valid_frame is not None:
            print(f"🩹 Padding {video_name} with last frame to reach {max_frames} frames")
            for i in range(saved_frame_count, max_frames):
                #save it again and again and again
                frame_filename = os.path.join(output_dir, f"frame_{i:03d}.jpg")
                cv2.imwrite(frame_filename, last_valid_frame)

        #finally close the video. destroy that VideoCapture object
        cap.release() 
        print(f"✅ Saved {max_frames} frames to {output_dir}")

        #appending a tuple of the name, pull duration, and the frames
        pull_data.append((video_name, pull_duration, max_frames))


    #writing the duration data to csv
    file_exists = os.path.exists(csv_path)

    # saying 'a' will make it append instead of keep writing new
    with open(csv_path, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(['Video_Name', 'Pull_Duration(s)', 'Frames_Saved'])
        writer.writerows(pull_data)

    print(f"\n📄 Pull durations saved to: {csv_path}")



############### MAIN 

#removed perfect and mid and added "good"
categories = ["good","under"]
for cat in categories:
    run_extraction(cat)
    print(f"✅ Gabruuuuuuu Completed {cat} category extraction\n")



