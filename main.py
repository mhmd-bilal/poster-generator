import streamlit as st
import cv2
import numpy as np
import os
import requests
import random
from urllib.parse import urlparse, urljoin

# Define global variables
REMOVE_BG_API_KEY = "JN9xfi6uXHbobeRzKcVjQeNg"  # Replace with your remove.bg API key
UNSPLASH_ACCESS_KEY = "iULWgWvhjToTRYK49rO2aRHbIotVetaOGntsf9fu4L4"
TEMP_PRODUCT_PATH = "temp_product_no_bg.png"

# Define functions
def get_background_color(product_image):
    gray = cv2.cvtColor(product_image, cv2.COLOR_BGR2GRAY)
    avg_pixel_value = np.mean(gray)
    if avg_pixel_value > 127:
        return "white"
    else:
        return "black"

def remove_background(image_path):
    # Call the remove.bg API to remove background
    files = {'image_file': open(image_path, 'rb')}
    params = {'size': 'auto'}
    headers = {'X-API-Key': REMOVE_BG_API_KEY}
    response = requests.post('https://api.remove.bg/v1.0/removebg', files=files, params=params, headers=headers)
    
    if response.status_code == 200:
        with open(TEMP_PRODUCT_PATH, 'wb') as f:
            f.write(response.content)
        return cv2.imread(TEMP_PRODUCT_PATH)
    else:
        print(f"Failed to remove background. Status code: {response.status_code}")
        return None

def merge_images(product_image_path, background_image_path, brand_name, output_path):
    # Load images with alpha channel (if present)
    product_image = cv2.imread(product_image_path, cv2.IMREAD_UNCHANGED)
    background_image = cv2.imread(background_image_path, cv2.IMREAD_UNCHANGED)

    # Resize product image to match background size
    product_height, product_width, _ = product_image.shape
    background_image = cv2.resize(background_image, (product_width, product_height))

    # Split product image into channels
    b, g, r, a = cv2.split(product_image)

    # Merge product image with background, applying alpha channel
    for c in range(3):
        background_image[..., c] = background_image[..., c] * (1 - (a / 255.0)) + product_image[..., c] * (a / 255.0)

    # Determine text color based on background color
    if np.mean(background_image) > 127:
        text_color = (0, 0, 0)  # Black text for bright background
    else:
        text_color = (255, 255, 255)  # White text for dark background

    # Add brand name with dynamically chosen text color
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    font_thickness = 2
    text_size = cv2.getTextSize(brand_name, font, font_scale, font_thickness)[0]
    text_x = int((product_width - text_size[0]) / 2)
    text_y = int(product_height - 20)  # Adjust position as needed
    cv2.putText(background_image, brand_name, (text_x, text_y), font, font_scale, text_color, font_thickness)

    # Save output image
    cv2.imwrite(output_path, background_image)

def download_background_images(prompt, output_dir, bg_color, num_images=5):
    # Adjust the prompt based on the background color
    if bg_color == "white":
        prompt += " dark"
    else:
        prompt += " white"
    
    # Download background images using the adjusted prompt
    search_url = "https://api.unsplash.com/search/photos"
    headers = {'Authorization': f'Client-ID {UNSPLASH_ACCESS_KEY}'}
    params = {'query': prompt, 'per_page': num_images}

    response = requests.get(search_url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        image_urls = [photo['urls']['regular'] for photo in data['results']]
        os.makedirs(output_dir, exist_ok=True)
        for i, image_url in enumerate(image_urls):
            try:
                response = requests.get(image_url)
                if response.status_code == 200:
                    image_data = response.content
                    with open(os.path.join(output_dir, f"background_{i+1}.jpg"), 'wb') as f:
                        f.write(image_data)
                else:
                    print(f"Failed to download image {i+1}. Status code: {response.status_code}")
            except Exception as e:
                print(f"Error downloading image {i+1}: {str(e)}")
    else:
        print(f"Failed to fetch images from Unsplash. Status code: {response.status_code}")

# Streamlit app
def main():
    st.title("Advertisement Poster Generator")

    # Upload product image
    product_image = st.file_uploader("Upload Product Image", type=["jpg", "png", "jpeg"])
    if product_image:
        # Display uploaded product image
        st.image(product_image, caption="Uploaded Product Image", use_column_width=True)

        # Get brand name from user
        brand_name = st.text_input("Enter Brand Name")

        # Get background image prompt from user
        background_prompt = st.text_input("Enter Background Image Prompt or Text Prompt")

        # Generate advertisement posters
        if st.button("Generate Posters"):
            st.write("Generating advertisement posters...")
            generate_posters(product_image, brand_name, background_prompt)

def generate_posters(product_image, brand_name, background_prompt):
    # Save uploaded product image temporarily
    with open(TEMP_PRODUCT_PATH, 'wb') as f:
        f.write(product_image.getvalue())

    # Remove background from product image using the remove.bg API
    product_image_no_bg = remove_background(TEMP_PRODUCT_PATH)

    if product_image_no_bg is not None:
        # Determine the background color of the product image
        bg_color = get_background_color(product_image_no_bg)

        # Download background images based on the background prompt
        download_background_images(background_prompt, "background_images", bg_color)

        # Pick a random background image from the downloaded images
        background_image_files = os.listdir("background_images")
        if background_image_files:
            for i, background_image_file in enumerate(random.sample(background_image_files, 5)):
                background_image_path = os.path.join("background_images", background_image_file)
                output_path = f"advertisement_poster_{i+1}.jpg"
                # Merge images and add brand name
                merge_images(TEMP_PRODUCT_PATH, background_image_path, brand_name, output_path)
                # Display generated poster
                st.image(output_path, caption=f"Advertisement Poster {i+1}", use_column_width=True)
        else:
            st.error("No background images found.")
    else:
        st.error("Background removal failed.")

if __name__ == "__main__":
    main()
