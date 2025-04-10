import os
import csv
import json
import re
import uuid
import subprocess
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
# Import PySceneDetect components.
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector

app = Flask(__name__, static_folder='static', template_folder='templates')

# Configuration
UPLOAD_FOLDER = 'static/videos'
ANNOTATION_FOLDER = 'static/annotations'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ANNOTATION_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ANNOTATION_FOLDER'] = ANNOTATION_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB max file size

# File extension whitelist
ALLOWED_EXTENSIONS = {'mp4', 'webm', 'mkv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/view')
def view_annotations():
    return render_template('view.html')

@app.route('/api/download', methods=['POST'])
def download_video():
    data = request.json
    youtube_url = data.get('url')
    youtube_id = re.search(r"v=([^&]+)", youtube_url).group(1)
    
    if not youtube_url:
        return jsonify({'error': 'No URL provided'}), 400
    
    try:
        # Generate a unique ID for this video
        # video_id = str(uuid.uuid4())
        video_id = youtube_id + '_' + str(uuid.uuid4())
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{video_id}.mp4")
        
        # Use yt-dlp to download the video
        # command = [
        #     'yt-dlp',
        #     '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        #     '-o', output_path,
        #     '--merge-output-format', 'mp4',
        #     youtube_url
        # ]
        command = [
            'yt-dlp',
            '-f', 'bestvideo[ext=mp4][height<=480]+bestaudio[ext=m4a]/best[ext=mp4][height<=480][acodec!=none]',
            '-o', output_path,
            '--merge-output-format', 'mp4',
            youtube_url
        ]


        
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            return jsonify({'error': f'Download failed: {stderr.decode()}'}), 500
        
        # Create a new annotation CSV file for this video
        csv_path = os.path.join(app.config['ANNOTATION_FOLDER'], f"video_{video_id}.csv")
        with open(csv_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                'video_id',
                'question_id', 
                'question_start_time', 
                'question_stop_time', 
                'question_text', 
                'answer_choices', 
                'correct_answer',
                'timestamp'
            ])
        
        # Extract original video title for display
        get_title_command = [
            'yt-dlp',
            '--get-title',
            youtube_url
        ]
        #title_process = subprocess.Popen(get_title_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Use encoding compatible with Windows (usually cp1252 or your local code page)
        title_process = subprocess.Popen(
            get_title_command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            encoding='utf-8',      # explicitly request utf-8 decoding
            errors='replace'       # replace problematic characters instead of raising exceptions
        )
        title_stdout, _ = title_process.communicate()
        #video_title = title_stdout.decode().strip() if title_process.returncode == 0 else "Untitled Video"
        video_title = title_stdout.strip() if title_process.returncode == 0 else "Untitled Video"
        
        # Return the video details
        return jsonify({
            'success': True,
            'video_id': video_id,
            'video_path': f"/static/videos/{video_id}.mp4",
            'video_title': video_title
        })
        
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/api/detect_shots', methods=['POST'])
def detect_shots():
    data = request.json
    video_id = data.get('video_id')
    
    if not video_id:
        return jsonify({'error': 'No video ID provided'}), 400
    
    video_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{video_id}.mp4")
    
    if not os.path.exists(video_path):
        return jsonify({'error': 'Video file not found'}), 404
    
    try:
        
        # Create a VideoManager and SceneManager.
        video_manager = VideoManager([video_path])
        scene_manager = SceneManager()
        # The threshold may need adjustment depending on your video content.
        scene_manager.add_detector(ContentDetector(threshold=30.0))
        
        # Start the video manager and perform scene detection.
        video_manager.start()
        scene_manager.detect_scenes(frame_source=video_manager)
        # Get a list of detected scenes; each scene is a tuple (start, end).
        scene_list = scene_manager.get_scene_list()
        # Release resources.
        video_manager.release()
        
        # Convert the scene boundaries into a list of dictionaries.
        shots = []
        for start_timecode, end_timecode in scene_list:
            start_sec = start_timecode.get_seconds()
            end_sec = end_timecode.get_seconds()
            shots.append({'start': start_sec, 'end': end_sec})
        
        # Retrieve video duration using ffprobe.
        duration_command = [
            'ffprobe', 
            '-v', 'error', 
            '-show_entries', 'format=duration', 
            '-of', 'default=noprint_wrappers=1:nokey=1', 
            video_path
        ]
        duration_process = subprocess.Popen(duration_command, stdout=subprocess.PIPE)
        duration_output = duration_process.communicate()[0]
        duration = float(duration_output.decode().strip())
        
        return jsonify({
            'success': True,
            'shots': shots,
            'duration': duration
        })
        
    except Exception as e:
        return jsonify({'error': f'Shot detection failed: {str(e)}'}), 500

# @app.route('/api/detect_shots', methods=['POST'])
# def detect_shots():
#     data = request.json
#     video_id = data.get('video_id')
    
#     if not video_id:
#         return jsonify({'error': 'No video ID provided'}), 400
    
#     video_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{video_id}.mp4")
    
#     if not os.path.exists(video_path):
#         return jsonify({'error': 'Video file not found'}), 404
    
#     try:
#         # This is a placeholder for actual shot detection
#         # In a real implementation, you would use PySceneDetect or a similar library
        
#         # For demonstration, we'll return synthetic shot boundaries
#         # In a real implementation, replace this with actual shot detection code
#         import random
        
#         # Get video duration using ffprobe
#         duration_command = [
#             'ffprobe', 
#             '-v', 'error', 
#             '-show_entries', 'format=duration', 
#             '-of', 'default=noprint_wrappers=1:nokey=1', 
#             video_path
#         ]
        
#         duration_process = subprocess.Popen(duration_command, stdout=subprocess.PIPE)
#         duration_output = duration_process.communicate()[0]
#         duration = float(duration_output.decode().strip())
        
#         # Generate mock shot boundaries (in a real app, use PySceneDetect)
#         num_shots = int(duration / 5)  # Assume a shot every ~5 seconds on average
#         shots = sorted([random.uniform(0, duration) for _ in range(num_shots)])
        
#         return jsonify({
#             'success': True,
#             'shots': shots,
#             'duration': duration
#         })
        
#     except Exception as e:
#         return jsonify({'error': f'Shot detection failed: {str(e)}'}), 500

@app.route('/api/save_annotation', methods=['POST'])
def save_annotation():
    data = request.json
    
    # Validate required fields
    required_fields = ['video_id', 'start_time', 'stop_time', 'question', 'answer_choices', 'correct_answer']
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
    
    video_id = data['video_id']
    csv_path = os.path.join(app.config['ANNOTATION_FOLDER'], f"video_{video_id}.csv")
    
    if not os.path.exists(csv_path):
        return jsonify({'error': 'Annotation file not found'}), 404
    
    try:
        # Generate a unique question ID
        question_id = str(uuid.uuid4())
        
        # Convert answer choices to JSON string
        answer_choices_json = json.dumps(data['answer_choices'])
        
        # Get current timestamp
        timestamp = datetime.now().isoformat()
        
        # Append the new annotation to the CSV
        with open(csv_path, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                video_id,
                question_id,
                data['start_time'],
                data['stop_time'],
                data['question'],
                answer_choices_json,
                data['correct_answer'],
                timestamp
            ])
        
        return jsonify({
            'success': True,
            'question_id': question_id
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to save annotation: {str(e)}'}), 500

@app.route('/api/get_annotations', methods=['GET'])
def get_annotations():
    video_id = request.args.get('video_id')
    
    if not video_id:
        # If no specific video is requested, return a list of all videos
        videos = []
        for filename in os.listdir(app.config['ANNOTATION_FOLDER']):
            if filename.startswith('video_') and filename.endswith('.csv'):
                vid_id = filename[6:-4]  # Extract ID from "video_ID.csv"
                
                # Count the number of annotations
                csv_path = os.path.join(app.config['ANNOTATION_FOLDER'], filename)
                with open(csv_path, 'r') as csvfile:
                    reader = csv.reader(csvfile)
                    next(reader)  # Skip header
                    annotation_count = sum(1 for _ in reader)
                
                videos.append({
                    'video_id': vid_id,
                    'annotation_count': annotation_count
                })
        
        return jsonify({'videos': videos})
    
    # If a specific video is requested, return its annotations
    csv_path = os.path.join(app.config['ANNOTATION_FOLDER'], f"video_{video_id}.csv")
    
    if not os.path.exists(csv_path):
        return jsonify({'error': 'Annotation file not found'}), 404
    
    try:
        annotations = []
        with open(csv_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Parse the JSON string back to a list
                row['answer_choices'] = json.loads(row['answer_choices'])
                annotations.append(row)
        
        # Determine if video file still exists
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{video_id}.mp4")
        video_exists = os.path.exists(video_path)
        
        return jsonify({
            'video_id': video_id,
            'video_path': f"/static/videos/{video_id}.mp4" if video_exists else None,
            'annotations': annotations
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve annotations: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)
