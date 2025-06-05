from moviepy.video.fx.all import fadein, fadeout

def add_cross_dissolve_transitions(self, clips: List[CompositeVideoClip], transition_duration: float = 1.0) -> CompositeVideoClip:
    """Add cross-dissolve transitions while syncing audio correctly (MoviePy 2.2.1 compatible)."""
    if len(clips) <= 1:
        return clips[0] if clips else None

    if self.progress_tracker:
        self.progress_tracker.update("Adding transitions", f"Using duration: {transition_duration:.1f}s")

    final_clips = []
    start_time = 0
    previous_audio_end = 0

    for i, clip in enumerate(clips):
        audio = clip.audio
        video = clip.without_audio()

        # Apply fadein/fadeout to the video (not to CompositeVideoClip)
        if i > 0:
            video = fadein(video, duration=transition_duration)
        if i < len(clips) - 1:
            video = fadeout(video, duration=transition_duration)

        # Set video start (allows visual overlap)
        video = video.set_start(start_time)

        # Set audio to start only after previous audio ends (no overlap)
        audio_start = max(start_time, previous_audio_end)
        audio = audio.set_start(audio_start)

        # Combine them into a composite (now with fades)
        composite = CompositeVideoClip([video]).set_audio(audio)
        final_clips.append(composite)

        # Move visual start time forward, but not the full clip duration due to visual overlap
        start_time += clip.duration - transition_duration
        previous_audio_end = audio_start + audio.duration

    # Combine all clips into a final video
    final_video = CompositeVideoClip(final_clips)
    return final_video
