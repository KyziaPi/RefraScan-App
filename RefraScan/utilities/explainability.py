import os
import cv2
import tensorflow as tf
import numpy as np

def make_gradcam_heatmap(model, image, metadata=None, class_index=None, layer_name=None):
    """
    Generate a Grad-CAM heatmap for an image-only or image+metadata model.

    `image` should already be preprocessed and have shape (1, H, W, 3).
    For the thesis, the target class should normally be the model's predicted
    class unless a specific true-class explanation is desired.
    """
    if layer_name is None:
        # Support both nested-backbone models and flat Keras applications
        # models (e.g., the current ResNet50 final model).
        backbone_candidates = [
            layer for layer in model.layers
            if "backbone" in layer.name
        ]

        if backbone_candidates:
            backbone = backbone_candidates[0]
            conv_layers = [
                layer for layer in backbone.layers
                if isinstance(layer, tf.keras.layers.Conv2D)
                and getattr(layer.output, "shape", None) is not None
                and len(layer.output.shape) == 4
            ]
            if not conv_layers:
                raise ValueError("No convolutional layer found inside the CNN backbone.")
            layer_name = conv_layers[-1].name

        else:
            # The current final model exposes ResNet50 layers directly.
            conv_layers = [
                layer for layer in model.layers
                if isinstance(layer, tf.keras.layers.Conv2D)
                and getattr(layer.output, "shape", None) is not None
                and len(layer.output.shape) == 4
            ]
            if not conv_layers:
                raise ValueError("No convolutional layer found for Grad-CAM.")
            layer_name = conv_layers[-1].name

    grad_model = tf.keras.models.Model(
        inputs=model.inputs,
        outputs=[model.get_layer(layer_name).output, model.output],
    )

    
    # Support both image-only and image+age models. For image+age, the caller
    # should provide the actual scaled age value for the selected record.
    if isinstance(model.input, list):
        if metadata is None:
            raise ValueError("metadata is required for Grad-CAM on an image+metadata model.")
        model_inputs = {
            "image_input": tf.convert_to_tensor(image, dtype=tf.float32),
            "meta_input": tf.convert_to_tensor(metadata, dtype=tf.float32)
        }
        
    else:
        # Wrap image array into dictionary using the input tensor's name
        # .split(':')[0] ensures we strip any trailing tensor indices like ':0'
        input_key = model.input.name.split(':')[0]  
        model_inputs = {input_key: image}

    with tf.GradientTape() as tape:
        # Pass formatted model_inputs dictionary
        conv_outputs, predictions = grad_model(model_inputs, training=False)
        
        if class_index is None:
            class_index = tf.argmax(predictions[0])
        class_score = predictions[:, class_index]

    grads = tape.gradient(class_score, conv_outputs)
    pooled_grads = tf.reduce_mean(grads, axis=(1, 2))
    conv_outputs = conv_outputs[0]
    pooled_grads = pooled_grads[0]
    heatmap = tf.reduce_sum(conv_outputs * pooled_grads, axis=-1)
    heatmap = tf.maximum(heatmap, 0) / (tf.reduce_max(heatmap) + 1e-8)
    return heatmap.numpy(), int(class_index)


def overlay_gradcam(original_rgb, heatmap, alpha=0.4):
    """Resize the heatmap and overlay it on the original fundus image."""
    heatmap = cv2.resize(heatmap, (original_rgb.shape[1], original_rgb.shape[0]))
    heatmap_uint8 = np.uint8(255 * heatmap)
    heatmap_color = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
    heatmap_color = cv2.cvtColor(heatmap_color, cv2.COLOR_BGR2RGB)
    overlay = cv2.addWeighted(original_rgb.astype(np.uint8), 1 - alpha, heatmap_color, alpha, 0)
    return overlay
    

# =========================================================
# MAIN PUBLIC WRAPPER FUNCTION
# =========================================================
def generate_and_save_gradcam(
    model, 
    processed_img, 
    display_img, 
    output_folder, 
    filename, 
    metadata=None,
    class_index=None, 
    alpha=0.4):
    """
    Single interface function:
    1. Generates the Grad-CAM heatmap.
    2. Overlays it onto the original fundus image.
    3. Saves the resulting overlay image to output_folder.
    4. Returns the relative web path for Flask context rendering.
    """
    # 1. Ensure metadata tensor has a batch dimension if provided
    if metadata is not None and len(np.array(metadata).shape) == 1:
        metadata = np.expand_dims(metadata, axis=0)

    # 2. Compute raw heatmap using the preprocessed tensor and metadata
    heatmap, _ = make_gradcam_heatmap(
        model=model,
        image=processed_img,
        metadata=metadata,
        class_index=class_index
    )

    # 3. Generate overlay using the clean, padded RGB image
    overlay_rgb = overlay_gradcam(display_img, heatmap, alpha=alpha)
    overlay_bgr = cv2.cvtColor(overlay_rgb, cv2.COLOR_RGB2BGR)

    # 4. Save heatmap image to disk
    heatmap_filename = f"heatmap_{filename}"
    heatmap_filepath = os.path.join(output_folder, heatmap_filename)
    cv2.imwrite(heatmap_filepath, overlay_bgr)

    # 5. Return relative path for web rendering
    return os.path.join('uploads/heatmaps', heatmap_filename).replace("\\", "/")