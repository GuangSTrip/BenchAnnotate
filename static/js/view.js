// YouTube Video Annotation Tool - View Script

// Global state
let state = {
    videoId: null,
    videoPath: null,
    annotations: [],
    selectedAnnotation: null
};

// DOM Elements
const elements = {
    videoListSection: document.getElementById('video-list-section'),
    videoGrid: document.getElementById('video-grid'),
    videoAnnotationsSection: document.getElementById('video-annotations-section'),
    annotationsTitle: document.getElementById('annotations-title'),
    annotationPlayer: document.getElementById('annotation-player'),
    annotationList: document.getElementById('annotation-list'),
    annotationDetails: document.getElementById('annotation-details'),
    questionDetails: document.getElementById('question-details'),
    backToList: document.getElementById('back-to-list')
};

// Initialize the application
function init() {
    // Set up event listeners
    elements.backToList.addEventListener('click', showVideoList);
    
    // Load available videos
    loadVideos();
}

// Load list of available videos
async function loadVideos() {
    try {
        const response = await fetch('/api/get_annotations');
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to load videos');
        }
        
        // Display the videos
        renderVideoList(data.videos);
        
    } catch (error) {
        console.error('Error loading videos:', error);
        elements.videoGrid.innerHTML = `<p class="status-error">Error loading videos: ${error.message}</p>`;
    }
}

// Render the list of videos with annotations
function renderVideoList(videos) {
    elements.videoGrid.innerHTML = '';
    
    if (videos.length === 0) {
        elements.videoGrid.innerHTML = '<p>No annotated videos available.</p>';
        return;
    }
    
    videos.forEach(video => {
        const videoCard = document.createElement('div');
        videoCard.className = 'video-card';
        videoCard.innerHTML = `
            <div class="video-thumbnail">
                <i class="fas fa-film fa-3x"></i>
            </div>
            <div class="video-info">
                <h3>Video ${video.video_id.substring(0, 8)}...</h3>
                <p><span class="annotation-count">${video.annotation_count} annotations</span></p>
                <button class="primary-btn view-annotations-btn" data-id="${video.video_id}">
                    <i class="fas fa-eye"></i> View Annotations
                </button>
            </div>
        `;
        
        videoCard.querySelector('.view-annotations-btn').addEventListener('click', () => {
            loadVideoAnnotations(video.video_id);
        });
        
        elements.videoGrid.appendChild(videoCard);
    });
}

// Load annotations for a specific video
async function loadVideoAnnotations(videoId) {
    try {
        const response = await fetch(`/api/get_annotations?video_id=${videoId}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to load annotations');
        }
        
        // Update state
        state.videoId = data.video_id;
        state.videoPath = data.video_path;
        state.annotations = data.annotations;
        state.selectedAnnotation = null;
        
        // Show the annotations view
        showAnnotationsView(data);
        
    } catch (error) {
        console.error('Error loading annotations:', error);
        alert(`Error loading annotations: ${error.message}`);
    }
}

// Show the annotations view for a video
function showAnnotationsView(data) {
    // Hide video list and show annotations view
    elements.videoListSection.classList.add('hidden');
    elements.videoAnnotationsSection.classList.remove('hidden');
    
    // Set the video title
    elements.annotationsTitle.textContent = `Annotations for Video ${data.video_id.substring(0, 8)}...`;
    
    // Load video if available
    if (data.video_path) {
        elements.annotationPlayer.src = data.video_path;
        elements.annotationPlayer.classList.remove('hidden');
    } else {
        elements.annotationPlayer.classList.add('hidden');
    }
    
    // Render the annotations list
    renderAnnotationList(data.annotations);
}

// Render the list of annotations
function renderAnnotationList(annotations) {
    elements.annotationList.innerHTML = '';
    
    if (annotations.length === 0) {
        elements.annotationList.innerHTML = '<p>No annotations found for this video.</p>';
        return;
    }
    
    annotations.forEach((annotation, index) => {
        const item = document.createElement('div');
        item.className = 'annotation-item';
        item.dataset.id = annotation.question_id;
        
        item.innerHTML = `
            <h3>Q${index + 1}: ${truncateText(annotation.question_text, 50)}</h3>
            <p><small>${formatTime(annotation.question_start_time)} - ${formatTime(annotation.question_stop_time)}</small></p>
        `;
        
        item.addEventListener('click', () => {
            selectAnnotation(annotation, index);
        });
        
        elements.annotationList.appendChild(item);
    });
}

// Select and display an annotation
function selectAnnotation(annotation, index) {
    // Update state
    state.selectedAnnotation = annotation;
    
    // Highlight the selected item
    document.querySelectorAll('.annotation-item').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelector(`.annotation-item[data-id="${annotation.question_id}"]`).classList.add('active');
    
    // Show annotation details
    elements.annotationDetails.classList.remove('hidden');
    
    // Parse the answer choices (stored as a JSON string)
    // let answerChoices = [];
    // try {
    //     answerChoices = JSON.parse(annotation.answer_choices);
    // } catch (e) {
    //     console.error('Error parsing answer choices:', e);
    // }

    // Handle the answer choices (could be string or already parsed)
    let answerChoices = [];

    if (typeof annotation.answer_choices === 'string') {
        // If it's a string, try parsing it
        try {
            answerChoices = JSON.parse(annotation.answer_choices);
        } catch (e) {
            console.error('Error parsing answer choices:', e);
            // Fallback to showing as a single answer if parsing fails
            answerChoices = [annotation.answer_choices];
        }
    } else if (Array.isArray(annotation.answer_choices)) {
        // If it's already an array (deserialized by backend)
        answerChoices = annotation.answer_choices;
    }
    
    // Format the details view
    elements.questionDetails.innerHTML = `
        <div class="question-detail">
            <strong>Question ${index + 1}:</strong> ${annotation.question_text}
        </div>
        <div class="question-detail">
            <strong>Time Range:</strong> ${formatTime(annotation.question_start_time)} - ${formatTime(annotation.question_stop_time)}
        </div>
        <div class="question-detail">
            <strong>Answer Choices:</strong>
            <ul class="answer-list">
                ${answerChoices.map((choice, i) => `
                    <li class="${i == annotation.correct_answer ? 'correct-answer' : ''}">
                        ${choice} ${i == annotation.correct_answer ? '✓' : ''}
                    </li>
                `).join('')}
            </ul>
        </div>
        <button class="primary-btn play-segment-btn">
            <i class="fas fa-play"></i> Play This Segment
        </button>
    `;
    
    // Add event listener to play button
    elements.questionDetails.querySelector('.play-segment-btn').addEventListener('click', () => {
        playAnnotationSegment(annotation);
    });
    
    // If video is available, seek to start of annotation
    if (state.videoPath && elements.annotationPlayer.src) {
        elements.annotationPlayer.currentTime = parseFloat(annotation.question_start_time);
    }
}

// Play a specific annotation segment
function playAnnotationSegment(annotation) {
    if (!elements.annotationPlayer.src) return;
    
    elements.annotationPlayer.currentTime = parseFloat(annotation.question_start_time);
    elements.annotationPlayer.play();
    
    // Set up event listener to pause at end of segment
    const pauseAtEnd = () => {
        if (elements.annotationPlayer.currentTime >= parseFloat(annotation.question_stop_time)) {
            elements.annotationPlayer.pause();
            elements.annotationPlayer.removeEventListener('timeupdate', pauseAtEnd);
        }
    };
    
    elements.annotationPlayer.addEventListener('timeupdate', pauseAtEnd);
}

// Go back to video list view
function showVideoList() {
    elements.videoAnnotationsSection.classList.add('hidden');
    elements.videoListSection.classList.remove('hidden');
    
    // Stop video playback if active
    if (elements.annotationPlayer.src) {
        elements.annotationPlayer.pause();
    }
}

// Helper Functions

// Format time in seconds to MM:SS format
function formatTime(seconds) {
    seconds = parseFloat(seconds);
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}

// Truncate text with ellipsis if too long
function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', init);
