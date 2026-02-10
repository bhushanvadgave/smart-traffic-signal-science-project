import cv2
import numpy as np

class CarCounter:
    def __init__(self):
        self.cap = None
        self.setup_camera()
        
        # Background subtractor for motion detection
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(detectShadows=True)
        
        # Contour filtering parameters
        self.min_contour_area = 500  # Minimum area for a detected object
        self.max_contour_area = 5000  # Maximum area for a detected object
        
    def setup_camera(self):
        """Setup camera, preferring external webcam"""
        print("Attempting to access camera...")
        print("If this is the first time, macOS may ask for camera permission.")
        
        # Try external camera first (index 1), then built-in (index 0)
        for camera_index in [1, 0]:
            print(f"Trying camera {camera_index}...")
            self.cap = cv2.VideoCapture(camera_index)
            
            if self.cap.isOpened():
                # Test if we can actually read frames
                ret, frame = self.cap.read()
                if ret:
                    # Set camera resolution
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    print(f"✓ Successfully using camera {camera_index}")
                    return
                else:
                    print(f"✗ Camera {camera_index} opens but cannot read frames")
                    self.cap.release()
            else:
                print(f"✗ Cannot open camera {camera_index}")
        
        # If we get here, no camera worked
        print("\n❌ ERROR: Could not access any camera!")
        print("📋 Troubleshooting steps:")
        print("1. Grant camera permission to Terminal in System Preferences > Security & Privacy > Camera")
        print("2. Make sure your external webcam is connected")
        print("3. Try running the script again after granting permissions")
        raise Exception("Could not open any camera - check permissions")
    
    def preprocess_frame(self, frame):
        """Preprocess frame for better object detection"""
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        return blurred
    
    def detect_objects(self, frame):
        """Detect objects using background subtraction and contour analysis"""
        # Preprocess frame
        processed = self.preprocess_frame(frame)
        
        # Apply background subtraction
        fg_mask = self.bg_subtractor.apply(frame)
        
        # Remove noise using morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by area
        valid_contours = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if self.min_contour_area < area < self.max_contour_area:
                valid_contours.append(contour)
        
        return valid_contours, fg_mask
    
    def count_objects_by_region(self, contours, frame_width):
        """Count objects in left and right regions"""
        left_count = 0
        right_count = 0
        mid_x = frame_width // 2
        
        object_centers = []
        
        for contour in contours:
            # Get bounding box
            x, y, w, h = cv2.boundingRect(contour)
            
            # Calculate center point
            center_x = x + w // 2
            center_y = y + h // 2
            object_centers.append((center_x, center_y))
            
            # Count based on which side of the center line
            if center_x < mid_x:
                left_count += 1
            else:
                right_count += 1
        
        return left_count, right_count, object_centers
    
    def draw_visualizations(self, frame, contours, object_centers, left_count, right_count):
        """Draw bounding boxes, center line, and counts on frame"""
        height, width = frame.shape[:2]
        mid_x = width // 2
        
        # Draw center dividing line
        cv2.line(frame, (mid_x, 0), (mid_x, height), (0, 0, 255), 3)
        
        # Draw bounding boxes and centers
        for i, contour in enumerate(contours):
            x, y, w, h = cv2.boundingRect(contour)
            center_x, center_y = object_centers[i]
            
            # Color based on region
            color = (255, 0, 0) if center_x < mid_x else (0, 255, 0)  # Blue for left, Green for right
            
            # Draw bounding box
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            
            # Draw center point
            cv2.circle(frame, (center_x, center_y), 5, color, -1)
        
        # Add text overlay
        result_text = f"Left: {left_count}  Right: {right_count}"
        if left_count > right_count:
            result_text += "  -> LEFT has more"
        elif right_count > left_count:
            result_text += "  -> RIGHT has more"
        else:
            result_text += "  -> Equal"
        
        cv2.putText(frame, result_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, "Press 'q' to quit", (10, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame
    
    def run(self):
        """Main loop for object detection and counting"""
        print("Starting car counter...")
        print("Position your camera to view the paper with toy cars")
        print("Press 'q' to quit")
        
        frame_count = 0
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Skip first few frames to let background subtractor stabilize
            if frame_count < 30:
                cv2.imshow('Car Counter', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                continue
            
            # Detect objects
            contours, fg_mask = self.detect_objects(frame)
            
            # Count objects by region
            left_count, right_count, object_centers = self.count_objects_by_region(contours, frame.shape[1])
            
            # Draw visualizations
            display_frame = self.draw_visualizations(frame, contours, object_centers, left_count, right_count)
            
            # Display results
            cv2.imshow('Car Counter', display_frame)
            cv2.imshow('Background Subtraction', fg_mask)
            
            # Print results to console
            if frame_count % 30 == 0:  # Print every 30 frames (roughly every second)
                print(f"Left: {left_count}, Right: {right_count} -> ", end="")
                if left_count > right_count:
                    print("LEFT has more cars")
                elif right_count > left_count:
                    print("RIGHT has more cars")
                else:
                    print("Equal distribution")
            
            # Exit on 'q' key press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        # Cleanup
        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        counter = CarCounter()
        counter.run()
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure you have opencv-python installed: pip install opencv-python")