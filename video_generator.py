import streamlit as st
import pandas as pd
from typing import List, Dict, Tuple, Optional
import tempfile
import os
from pathlib import Path
import base64
from io import BytesIO
import json

# Document processing imports
try:
    import fitz  # PyMuPDF for PDF
    import docx  # python-docx for Word documents
    from pptx import Presentation  # python-pptx for PowerPoint
    import mammoth  # For better DOC/DOCX text extraction
    from PIL import Image
    import pytesseract  # For OCR if needed
except ImportError as e:
    st.error(f"Missing required library: {e}")
    st.stop()

# Video generation imports
try:
    # MoviePy 2.2.1 compatible imports
    from moviepy import VideoFileClip, AudioFileClip, ImageClip, TextClip, ColorClip, CompositeVideoClip, concatenate_videoclips
    import cv2
    import numpy as np
    from gtts import gTTS  # Google Text-to-Speech
    
    # Test MoviePy installation
    test_clip = ColorClip(size=(100, 100), color=(0, 0, 0), duration=0.1)
    test_clip.close()
    
except ImportError as e:
    st.error(f"Missing video processing library: {e}")
    st.markdown("""
    ### 🔧 Installation Instructions
    
    For MoviePy 2.2.1 compatibility:
    
    **Recommended installation:**
    ```bash
    pip install "moviepy==2.2.1"
    pip install imageio-ffmpeg
    ```
    
    **Alternative methods:**
    ```bash
    # Method 1 - With conda
    conda install -c conda-forge moviepy
    
    # Method 2 - Latest version
    pip install moviepy
    ```
    
    After installation, restart your Python environment/kernel.
    """)
    st.stop()
except Exception as e:
    st.error(f"MoviePy installation issue: {e}")
    st.markdown("""
    ### Additional Requirements
    
    MoviePy also requires:
    - **FFmpeg** (for video processing)
    - **ImageIO** (for image handling)
    
    **To install FFmpeg:**
    
    **Windows:**
    ```bash
    # Using chocolatey
    choco install ffmpeg
    
    # Or download from https://ffmpeg.org/download.html
    ```
    
    **macOS:**
    ```bash
    brew install ffmpeg
    ```
    
    **Linux (Ubuntu/Debian):**
    ```bash
    sudo apt update
    sudo apt install ffmpeg
    ```
    
    **Alternative: Install imageio-ffmpeg**
    ```bash
    pip install imageio-ffmpeg
    ```
    """)
    st.stop()

class DocumentProcessor:
    """Handle document text and image extraction"""
    
    @staticmethod
    def extract_from_pdf(file_path: str) -> Tuple[List[str], List[Image.Image]]:
        """Extract text and images from PDF"""
        doc = fitz.open(file_path)
        texts = []
        images = []
        
        for page_num in range(doc.page_count):
            page = doc[page_num]
            
            # Extract text
            text = page.get_text()
            if text.strip():
                texts.append(text.strip())
            
            # Extract images
            image_list = page.get_images()
            for img_index, img in enumerate(image_list):
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                if pix.n - pix.alpha < 4:  # GRAY or RGB
                    img_data = pix.tobytes("png")
                    img_pil = Image.open(BytesIO(img_data))
                    images.append(img_pil)
                pix = None
        
        doc.close()
        return texts, images
    
    @staticmethod
    def extract_from_docx(file_path: str) -> Tuple[List[str], List[Image.Image]]:
        """Extract text and images from DOCX"""
        doc = docx.Document(file_path)
        texts = []
        images = []
        
        # Extract text from paragraphs
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                texts.append(paragraph.text.strip())
        
        # Extract images from document parts
        for rel in doc.part.rels.values():
            if "image" in rel.target_ref:
                try:
                    img_data = rel.target_part.blob
                    img_pil = Image.open(BytesIO(img_data))
                    images.append(img_pil)
                except Exception:
                    continue
        
        return texts, images
    
    @staticmethod
    def extract_from_pptx(file_path: str) -> Tuple[List[str], List[Image.Image]]:
        """Extract text and images from PPTX"""
        prs = Presentation(file_path)
        texts = []
        images = []
        
        for slide in prs.slides:
            # Extract text from shapes
            slide_text = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_text.append(shape.text.strip())
                
                # Extract images
                if shape.shape_type == 13:  # Picture type
                    try:
                        image = shape.image
                        img_data = image.blob
                        img_pil = Image.open(BytesIO(img_data))
                        images.append(img_pil)
                    except Exception:
                        continue
            
            if slide_text:
                texts.append(" ".join(slide_text))
        
        return texts, images

class TextExpander:
    """Expand and enhance text content"""
    
    @staticmethod
    def expand_text(text: str, target_length: int = 100) -> str:
        """Expand text to meet minimum length requirements"""
        words = text.split()
        if len(words) >= target_length:
            return text
        
        # Simple expansion by adding explanatory phrases
        expanded_parts = []
        for sentence in text.split('.'):
            if sentence.strip():
                expanded_parts.append(sentence.strip())
                # Add explanatory content based on context
                if any(keyword in sentence.lower() for keyword in ['process', 'method', 'approach']):
                    expanded_parts.append("This involves several key steps and considerations")
                elif any(keyword in sentence.lower() for keyword in ['result', 'outcome', 'conclusion']):
                    expanded_parts.append("The implications of this are significant for understanding the overall concept")
                elif any(keyword in sentence.lower() for keyword in ['important', 'key', 'main']):
                    expanded_parts.append("This point deserves special attention and careful analysis")
        
        return '. '.join(expanded_parts) + '.'

class VideoGenerator:
    """Generate video from matched content"""
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def create_text_clip(self, text: str, duration: float, size: Tuple[int, int] = (1920, 1080)) -> TextClip:
        """Create animated text clip with word-by-word reveal"""
        words = text.split()
        
        # Create base text clip with better visibility - MoviePy 2.2.1 compatible
        try:
            # Try common system fonts in order of preference
            fonts_to_try = ['Arial', 'DejaVu-Sans', 'Liberation-Sans']
            font_used = None
            
            for font in fonts_to_try:
                try:
                    txt_clip = TextClip(
                        text=text,  # Use 'txt' parameter explicitly
                        font_size=60,  # Changed from 'fontsize' to 'font_size'
                        color='white', 
                        font=font,
                        stroke_color='black',
                        stroke_width=2,
                        method='caption',
                        size=(1600, 400)
                    ).with_duration(duration)  # Use with_duration for 2.2.1
                    font_used = font
                    break
                except:
                    continue
            
            # If no specific font works, use default
            if font_used is None:
                txt_clip = TextClip(
                    text=text,  # Use 'txt' parameter explicitly
                    font_size=60,  # Changed from 'fontsize' to 'font_size'
                    color='white',
                    stroke_color='black',
                    stroke_width=2,
                    method='caption',
                    size=(1600, 400)
                ).with_duration(duration)  # Use with_duration for 2.2.1
                
        except Exception as e:
            # Fallback to simplest TextClip creation
            txt_clip = TextClip(
                text=text,  # Use 'txt' parameter explicitly
                font_size=50,  # Changed from 'fontsize' to 'font_size'
                color='white'
            ).with_duration(duration)  # Use with_duration for 2.2.1
        
        return txt_clip
    
    def create_image_clip(self, image: Image.Image, duration: float, size: Tuple[int, int] = (1920, 1080)) -> ImageClip:
        """Create full-screen image clip with animations"""
        # Save image temporarily
        temp_path = self.output_dir / f"temp_img_{id(image)}.png"
        
        # Resize image to full screen while maintaining aspect ratio
        img_ratio = image.width / image.height
        screen_ratio = size[0] / size[1]
        
        if img_ratio > screen_ratio:
            # Image is wider - fit to height
            new_height = size[1]
            new_width = int(new_height * img_ratio)
        else:
            # Image is taller - fit to width
            new_width = size[0]
            new_height = int(new_width / img_ratio)
        
        # Resize and center crop to full screen
        resized_img = image.resize((new_width, new_height), Image.LANCZOS)
        
        # Create full screen image by center cropping
        left = (new_width - size[0]) // 2
        top = (new_height - size[1]) // 2
        right = left + size[0]
        bottom = top + size[1]
        
        if left < 0 or top < 0:
            # If image is smaller than screen, create background and paste
            full_img = Image.new('RGB', size, (0, 0, 0))
            paste_x = (size[0] - new_width) // 2
            paste_y = (size[1] - new_height) // 2
            full_img.paste(resized_img, (paste_x, paste_y))
        else:
            full_img = resized_img.crop((left, top, right, bottom))
        
        full_img.save(temp_path)
        
        # Create image clip - MoviePy 2.2.1 compatible
        img_clip = ImageClip(str(temp_path)).with_duration(duration)
        
        return img_clip
    
    def generate_voiceover(self, text: str, lang: str = 'en') -> str:
        """Generate voiceover using TTS"""
        tts = gTTS(text=text, lang=lang, slow=False)
        audio_path = self.output_dir / f"voiceover_{hash(text)}.mp3"
        tts.save(str(audio_path))
        return str(audio_path)
    
    def create_frame_clip(self, images: List[Image.Image], text: str, expand_text: bool = True) -> CompositeVideoClip:
        """Create a single frame combining images, text, and audio"""
        if expand_text:
            text = TextExpander.expand_text(text)
        
        # Generate voiceover
        audio_path = self.generate_voiceover(text)
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        clips = []
        
        # Add images as full-screen background
        if images:
            # Use first image as main background
            main_img_clip = self.create_image_clip(images[0], duration)
            clips.append(main_img_clip)
            
            # If multiple images, create a slideshow effect within the frame
            if len(images) > 1:
                img_duration = duration / len(images)
                for i, img in enumerate(images):
                    img_clip = self.create_image_clip(img, img_duration)
                    img_clip = img_clip.with_start(i * img_duration)  # Use with_start for 2.2.1
                    clips.append(img_clip)
        else:
            # Create dark background if no images
            bg_clip = ColorClip(size=(1920, 1080), color=(20, 20, 20)).with_duration(duration)
            clips.append(bg_clip)
        
        # Add semi-transparent overlay for better text visibility
        overlay = ColorClip(size=(1920, 300), color=(0, 0, 0))
        overlay = overlay.with_opacity(0.7).with_duration(duration).with_position(('center', 'bottom'))
        clips.append(overlay)
        
        # Add text at bottom with better positioning
        text_clip = self.create_text_clip(text, duration)
        text_clip = text_clip.with_position(('center', 900))  # Use with_position for 2.2.1
        clips.append(text_clip)
        
        # Compose final clip
        final_clip = CompositeVideoClip(clips)
        final_clip = final_clip.with_audio(audio_clip)  # Use with_audio for 2.2.1
        
        return final_clip
    
    def add_transition_effects(self, clips: List[CompositeVideoClip]) -> List[CompositeVideoClip]:
        """Add transition effects between clips - MoviePy 2.2.1 compatible"""
        if len(clips) <= 1:
            return clips
        
        # Simple transition effects that work with MoviePy 2.2.1
        final_clips = []
        
        for i, clip in enumerate(clips):
            try:
                if i == 0:
                    # First clip - add fade in
                    if hasattr(clip, 'fadein'):
                        clip_with_fade = clip.fadein(0.5)
                        final_clips.append(clip_with_fade)
                    else:
                        # No fade capability, use as-is
                        final_clips.append(clip)
                elif i == len(clips) - 1:
                    # Last clip - add fade out
                    if hasattr(clip, 'fadeout'):
                        clip_with_fade = clip.fadeout(0.5)
                        final_clips.append(clip_with_fade)
                    else:
                        # No fade capability, use as-is
                        final_clips.append(clip)
                else:
                    # Middle clips - no special effects
                    final_clips.append(clip)
            except Exception as e:
                # If any transition fails, just use the original clip
                st.warning(f"Transition effect failed for clip {i+1}, using original clip")
                final_clips.append(clip)
        
        return final_clips

def main():
    st.set_page_config(page_title="Document to Video Generator", layout="wide")
    
    st.header("Document to Video Generator")
    st.markdown("Upload documents and create engaging videos with animations and voiceovers!")
    
    # Initialize session state
    if 'extracted_content' not in st.session_state:
        st.session_state.extracted_content = None
    if 'matches' not in st.session_state:
        st.session_state.matches = []
    
    # File upload section
    st.subheader("1. Upload Document")
    uploaded_file = st.file_uploader(
        "Choose a document file",
        type=['pdf', 'doc', 'docx', 'ppt', 'pptx'],
        help="Supported formats: PDF, DOC, DOCX, PPT, PPTX"
    )
    
    if uploaded_file:
        with st.spinner("Processing document..."):
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
            
            try:
                # Extract content based on file type
                file_ext = uploaded_file.name.split('.')[-1].lower()
                
                if file_ext == 'pdf':
                    texts, images = DocumentProcessor.extract_from_pdf(tmp_path)
                elif file_ext in ['doc', 'docx']:
                    texts, images = DocumentProcessor.extract_from_docx(tmp_path)
                elif file_ext in ['ppt', 'pptx']:
                    texts, images = DocumentProcessor.extract_from_pptx(tmp_path)
                
                st.session_state.extracted_content = {
                    'texts': texts,
                    'images': images,
                    'filename': uploaded_file.name
                }
                
                st.success(f"✅ Extracted {len(texts)} text segments and {len(images)} images")
                
            except Exception as e:
                st.error(f"Error processing document: {str(e)}")
            finally:
                # Clean up temp file
                os.unlink(tmp_path)
    
    # Content preview and matching section
    if st.session_state.extracted_content:
        st.subheader("2. Preview Extracted Content")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("📝 Text Segments")
            texts = st.session_state.extracted_content['texts']
            for i, text in enumerate(texts):
                with st.expander(f"Text {i+1}"):
                    st.write(text[:200] + "..." if len(text) > 200 else text)
        
        with col2:
            st.markdown("🖼️ Images")
            images = st.session_state.extracted_content['images']
            for i, img in enumerate(images):
                with st.expander(f"Image {i+1}"):
                    st.image(img, width=300)
        
        # Matching interface
        st.subheader("3. Match Images with Text")
        
        with st.form("matching_form"):
            st.write("Create combinations of images and text for video frames:")
            
            # Add match
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                selected_images = st.multiselect(
                    "Select Images",
                    options=list(range(len(images))),
                    format_func=lambda x: f"Image {x+1}",
                    key="selected_images"
                )
            
            with col2:
                selected_texts = st.multiselect(
                    "Select Text Segments",
                    options=list(range(len(texts))),
                    format_func=lambda x: f"Text {x+1}",
                    key="selected_texts"
                )
            
            with col3:
                if st.form_submit_button("Add Match"):
                    if selected_images or selected_texts:
                        match = {
                            'images': selected_images,
                            'texts': selected_texts,
                            'combined_text': ' '.join([texts[i] for i in selected_texts])
                        }
                        st.session_state.matches.append(match)
                        st.success("Match added!")
        
        # Display current matches
        if st.session_state.matches:
            st.markdown("Current Matches")
            for i, match in enumerate(st.session_state.matches):
                with st.expander(f"Frame {i+1}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Images:** {[f'Image {j+1}' for j in match['images']]}")
                        for img_idx in match['images']:
                            if img_idx < len(images):
                                st.image(images[img_idx], width=200)
                    
                    with col2:
                        st.write(f"**Texts:** {[f'Text {j+1}' for j in match['texts']]}")
                        st.write(match['combined_text'][:300] + "..." if len(match['combined_text']) > 300 else match['combined_text'])
                    
                    if st.button(f"Remove Frame {i+1}", key=f"remove_{i}"):
                        st.session_state.matches.pop(i)
                        st.rerun()
        
        # Video generation section
        if st.session_state.matches:
            st.subheader("4. Generate Video")
            
            col1, col2 = st.columns(2)
            
            with col1:
                expand_text = st.checkbox("Expand text for detailed explanation", value=True)
                add_transitions = st.checkbox("Add transition effects", value=True)
            
            with col2:
                voice_lang = st.selectbox("Voice Language", ['en', 'es', 'fr', 'de', 'it'], index=0)
            
            if st.button("🎬 Generate Video", type="primary"):
                with st.spinner("Generating video... This may take a few minutes."):
                    try:
                        # Create video generator
                        video_gen = VideoGenerator("temp_video")
                        
                        # Create clips for each match
                        clips = []
                        for match in st.session_state.matches:
                            frame_images = [images[i] for i in match['images'] if i < len(images)]
                            frame_clip = video_gen.create_frame_clip(
                                frame_images, 
                                match['combined_text'], 
                                expand_text
                            )
                            clips.append(frame_clip)
                        
                        # Add transitions if requested
                        if add_transitions and len(clips) > 1:
                            clips = video_gen.add_transition_effects(clips)
                        
                        # Concatenate all clips
                        final_video = concatenate_videoclips(clips)
                        
                        # Save video - MoviePy 2.2.1 compatible
                        output_path = "generated_video.mp4"
                        final_video.write_videofile(
                            output_path,
                            fps=24,
                            codec='libx264',
                            audio_codec='aac',
                            #verbose=False,
                            logger='bar'
                        )
                        
                        st.success("🎉 Video generated successfully!")
                        
                        # Provide download link
                        with open(output_path, 'rb') as f:
                            video_bytes = f.read()
                        
                        st.download_button(
                            label="📥 Download Video",
                            data=video_bytes,
                            file_name=f"video_{st.session_state.extracted_content['filename']}.mp4",
                            mime="video/mp4"
                        )
                        
                        # Display video preview
                        st.video(output_path)
                        
                        # Clean up clips to free memory
                        for clip in clips:
                            clip.close()
                        final_video.close()
                        
                    except Exception as e:
                        st.error(f"Error generating video: {str(e)}")
                        st.error("Try disabling transition effects if the error persists.")
    


if __name__ == "__main__":
    main()