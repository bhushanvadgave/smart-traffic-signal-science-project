# Classical CV Car Counter

Uses OpenCV background subtraction to detect and count toy cars in left vs right sections.

## Setup
```bash
pip install -r requirements.txt
python car_counter.py
```

## How it works
1. **Background Subtraction**: Detects moving/new objects by comparing with background
2. **Contour Detection**: Finds object boundaries 
3. **Region Counting**: Counts objects left vs right of center line
4. **Real-time Display**: Shows bounding boxes and counts

## Usage
- Position camera to view paper with toy cars
- Let it run for ~1 second to build background model
- Place/move toy cars on paper
- Press 'q' to quit

## Features
- Automatic external webcam detection
- Real-time object counting
- Visual feedback with colored bounding boxes
- Console output every second