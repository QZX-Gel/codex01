from src.common.schema import TranscriptSegment, SlideSpan


def test_transcript_segment_creation():
    seg = TranscriptSegment(
        start_time=0.0,
        end_time=2.5,
        text="hello"
    )
    assert seg.start_time == 0.0
    assert seg.end_time == 2.5
    assert seg.text == "hello"


def test_slide_span_creation():
    slide = SlideSpan(
        page_id=1,
        start_time=0.0,
        end_time=10.0,
        keyframe_path="output/slides/keyframe_001.jpg"
    )
    assert slide.page_id == 1
    assert slide.start_time == 0.0
    assert slide.end_time == 10.0
    assert slide.keyframe_path.endswith(".jpg")