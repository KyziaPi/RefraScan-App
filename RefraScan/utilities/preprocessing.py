import cv2
import numpy as np
from tensorflow.keras.applications.resnet50 import preprocess_input as resnet_preprocess

def load_and_preprocess_image(img_path, target_size=(224, 224)):
    try:
        img = cv2.imread(img_path)
        if img is None:
            raise FileNotFoundError(f"Image not found at path: {img_path}")
            
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        h, w = img.shape[:2]
        th, tw = target_size
        scale = min(tw / w, th / h)
        nw, nh = int(w * scale), int(h * scale)
        
        resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)

        # Create canvas and center the image
        padded = np.zeros((th, tw, 3), dtype=np.uint8)
        top = (th - nh) // 2
        left = (tw - nw) // 2
        padded[top : top + nh, left : left + nw] = resized
        
        # 1. Keep a clean copy for the Grad-CAM visual overlay
        display_img = padded.copy()
        
        # 2. Preprocess the other copy for the AI model
        model_img = resnet_preprocess(padded.astype(np.float32))

        return display_img, model_img

    except Exception as e:
        # Return empty arrays on failure so unpacking doesn't crash
        return (
            np.zeros((target_size[0], target_size[1], 3), dtype=np.uint8), 
            np.zeros((target_size[0], target_size[1], 3), dtype=np.float32)
        )