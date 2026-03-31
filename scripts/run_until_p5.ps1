$ErrorActionPreference = "Stop"

Set-Location "H:\projects\codex01"

Write-Host "== Check input =="
if (-not (Test-Path "input\class.mp4")) {
    throw "Missing input\class.mp4"
}

Write-Host "== Prepare output dirs =="
New-Item -ItemType Directory -Force -Path output | Out-Null
New-Item -ItemType Directory -Force -Path output\frames | Out-Null
New-Item -ItemType Directory -Force -Path output\slides | Out-Null
New-Item -ItemType Directory -Force -Path output\meta | Out-Null
New-Item -ItemType Directory -Force -Path output\logs | Out-Null

Write-Host "== M1 extract audio =="
python -c "from src.ingest.extract_audio import extract_audio; print(extract_audio('input/class.mp4', 'output/audio.wav'))"

Write-Host "== M1 extract frames =="
python -c "from src.ingest.extract_frames import extract_frames; print(len(extract_frames('input/class.mp4', 'output/frames', 4)))"

Write-Host "== M2 transcribe =="
python -c "from src.asr.transcribe import transcribe_audio; print(len(transcribe_audio('output/audio.wav', 'small', 'cuda')))"

Write-Host "== M3 detect slides =="
python -c "from src.slide.detect_slides import detect_slide_spans; import glob; frames=sorted(glob.glob('output/frames/*.jpg')); slides=detect_slide_spans(frames, 0.82); print(len(slides))"

Write-Host "== M4 align =="
python -m src.align.align_text

Write-Host "== Check outputs =="
$files = @(
    "output\audio.wav",
    "output\transcript.jsonl",
    "output\page_manifest.json",
    "output\page_text_map.json"
)

foreach ($f in $files) {
    $ok = Test-Path $f
    Write-Host "$f -> $ok"
}

Write-Host "== P5 acceptance =="
python tests/e2e/check_p5_acceptance.py

Write-Host "== Done =="