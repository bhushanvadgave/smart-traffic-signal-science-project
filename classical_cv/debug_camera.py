import cv2

def test_cameras():
    """Test which cameras are available and working"""
    print("Testing camera availability...")
    
    for i in range(5):  # Test cameras 0-4
        print(f"\nTesting camera {i}:")
        cap = cv2.VideoCapture(i)
        
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"✓ Camera {i}: Working (frame shape: {frame.shape})")
                # Show a test frame
                cv2.imshow(f'Camera {i} Test', frame)
                cv2.waitKey(1000)  # Show for 1 second
                cv2.destroyAllWindows()
            else:
                print(f"✗ Camera {i}: Opens but can't read frames")
        else:
            print(f"✗ Camera {i}: Cannot open")
        
        cap.release()

if __name__ == "__main__":
    test_cameras()