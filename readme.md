


### Create Environment

```bash
mamba create -n vidannot python=3.12
mamba activate vidannot
```

### Install FFMPEG (to process videos)
```bash
mamba install ffmpeg
```

### Install Python Dependencies

```bash
pip install --upgrade "scenedetect[opencv]"
pip install Flask
pip install watchdog
pip install yt-dlp
```

### Run tool
```bash
python backend.py
```
