import streamlit as st
import pandas as pd
import os
import tempfile
from moviepy import *
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import base64
from gtts import gTTS
import pygame
from llm_response import get_llm_summary, image_to_base64, base64_to_image

# Configure Streamlit page
st.with_page_config(
    page_title="Document to Video Generator",
    page_icon="🎬",
    layout="wide"
)

def create_placeholder_image(text, size=(1280, 720)):
    """Create a placeholder image with text when no image is available"""
    img = Image.new('RGB', size, color='lightblue')
    draw = ImageDraw.Draw(img)
    
    try:
        # Try to use a default font
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        # Fallback to default font
        font = ImageFont.load_default()
    
    # Calculate text position to center it
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size[0] - text_width) // 2
    y = (size[1] - text_height) // 2
    
    draw.text((x, y), text, fill='darkblue', font=font)
    return img

def generate_audio(text, filename):
    """Generate audio from text using gTTS"""
    try:
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(filename)
        return filename
    except Exception as e:
        st.error(f"Error generating audio: {str(e)}")
        return None

def create_video_clip(image, description, duration=5):
    """Create a video clip from image and description"""
    
    # Create or process image
    if image is None:
        # Create placeholder image
        pil_image = create_placeholder_image(f"Step: {description[:50]}...")
    else:
        pil_image = image
    
    # Resize image to standard video dimensions
    pil_image = pil_image.resize((1280, 720), Image.Resampling.LANCZOS)
    
    # Convert PIL image to numpy array
    img_array = np.array(pil_image)
    
    # Create ImageClip
    clip = ImageClip(img_array, duration=duration)
    
    return clip

def generate_video_from_dataframe(df, output_path="output_video.mp4"):
    """Generate video from dataframe with images and descriptions"""
    clips = []
    audio_clips = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_steps = len(df)
    
    for i, row in df.iterrows():
        progress = (i + 1) / total_steps
        progress_bar.progress(progress)
        status_text.text(f"Processing step {i+1} of {total_steps}...")
        
        image = row['images']
        description = row['description']
        
        # Generate audio for this step
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_audio:
            audio_file = generate_audio(description, tmp_audio.name)
            
            if audio_file:
                # Load audio to get duration
                audio_clip = AudioFileClip(audio_file)
                duration = audio_clip.duration
                
                # Create video clip with the same duration as audio
                video_clip = create_video_clip(image, description, duration)
                video_clip = video_clip.with_audio(audio_clip)
                
                clips.append(video_clip)
                
                # Clean up temporary audio file
                os.unlink(audio_file)
            else:
                # Default duration if audio generation fails
                video_clip = create_video_clip(image, description, 5)
                clips.append(video_clip)
    
    if clips:
        # Concatenate all video clips
        status_text.text("Combining video clips...")
        final_video = concatenate_videoclips(clips)
        
        # Write the final video
        status_text.text("Writing final video...")
        final_video.write_videofile(
            output_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True
        )
        
        # Clean up
        final_video.close()
        for clip in clips:
            clip.close()
        
        progress_bar.progress(1.0)
        status_text.text("Video generation complete!")
        
        return output_path
    else:
        st.error("No video clips were generated.")
        return None

def main():
    st.title("🎬 Document to Video Generator")
    st.markdown("Upload a document (.doc, .docx, .ppt, .pptx, .pdf) and generate a tutorial video with voiceover!")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose a document file",
        type=['doc', 'docx', 'ppt', 'pptx', 'pdf'],
        help="Upload a document containing tutorial content"
    )
    
    if uploaded_file is not None:
        # Display file info
        st.success(f"File uploaded: {uploaded_file.name}")
        file_ext = uploaded_file.name.split('.')[-1].lower()
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        
        # Process document button
        if st.button("🔄 Process Document", type="primary"):
            with st.spinner("Processing document with LLM..."):
                # Get dataframe from LLM
                df = get_llm_summary(tmp_file_path, file_ext)
                
                # Store dataframe in session state
                st.session_state['df'] = df
                st.session_state['processed'] = True
        
        # Clean up temporary file
        if 'tmp_file_path' in locals():
            try:
                os.unlink(tmp_file_path)
            except:
                pass
    
    # Display processed data and generate video
    if st.session_state.get('processed', False) and 'df' in st.session_state:
        df = st.session_state['df']
        
        st.subheader("📋 Processed Steps")
        
        # Display dataframe content
        for i, row in df.iterrows():
            with st.expander(f"Step {i+1}", expanded=False):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    if row['images'] is not None:
                        st.image(row['images'], caption=f"Step {i+1} Image", use_column_width=True)
                    else:
                        st.info("No image available for this step")
                
                with col2:
                    st.write("**Description:**")
                    st.write(row['description'])
        
        # Generate video button
        st.subheader("🎬 Generate Video")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("🎥 Generate Video with Voiceover", type="primary"):
                with st.spinner("Generating video... This may take a few minutes."):
                    output_path = "tutorial_video.mp4"
                    video_file = generate_video_from_dataframe(df, output_path)
                    
                    if video_file and os.path.exists(video_file):
                        st.success("Video generated successfully!")
                        
                        # Provide download button
                        with open(video_file, 'rb') as f:
                            st.download_button(
                                label="📥 Download Video",
                                data=f.read(),
                                file_name="tutorial_video.mp4",
                                mime="video/mp4"
                            )
                        
                        # Display video
                        st.video(video_file)
                    else:
                        st.error("Failed to generate video.")
        
        with col2:
            if st.button("🔄 Reset"):
                st.session_state.clear()
                st.experimental_rerun()

# Sidebar with information
with st.sidebar:
    st.markdown("## ℹ️ How to Use")
    st.markdown("""
    1. **Upload Document**: Choose a .doc, .docx, .ppt, .pptx, or .pdf file
    2. **Process**: Click 'Process Document' to extract content and generate steps
    3. **Review**: Check the generated steps and images
    4. **Generate**: Click 'Generate Video' to create your tutorial video
    5. **Download**: Save the generated video to your device
    """)
    
    st.markdown("## 🛠️ Requirements")
    st.markdown("""
    - Local Ollama server running with qwen:latest model
    - Internet connection for text-to-speech
    - Sufficient disk space for video generation
    """)
    
    st.markdown("## 📋 Supported Formats")
    st.markdown("""
    - **Documents**: .doc, .docx
    - **Presentations**: .ppt, .pptx  
    - **PDFs**: .pdf
    """)

if __name__ == "__main__":
    # Initialize session state
    if 'processed' not in st.session_state:
        st.session_state['processed'] = False
    
    main()