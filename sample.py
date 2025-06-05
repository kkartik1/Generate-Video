def add_cross_dissolve_transitions(self, clips: List[CompositeVideoClip], transition_duration: float = 1.0) -> CompositeVideoClip:
    """Add cross-dissolve transitions while syncing audio properly (no audio overlap)."""
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

        # Fade in/out video for transition
        if i > 0:
            video = video.fadein(transition_duration)
        if i < len(clips) - 1:
            video = video.fadeout(transition_duration)

        # Set video start time for overlap
        video = video.set_start(start_time)
        
        # Set audio to start only after the previous audio finishes
        audio_start = max(start_time, previous_audio_end)
        audio = audio.set_start(audio_start)

        composite = CompositeVideoClip([video]).set_audio(audio)
        final_clips.append(composite)

        # Calculate next start time (video may overlap, but audio must be sequential)
        start_time += clip.duration - transition_duration
        previous_audio_end = audio_start + audio.duration

    # Combine all into final timeline
    final_video = CompositeVideoClip(final_clips)
    return final_video
