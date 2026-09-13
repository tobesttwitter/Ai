import os
import subprocess
import sys

import cv2
import numpy as np
import onnxruntime

sys.path.insert(0, "/tmp/wav2lip-onnx")

import audio
from hparams import hparams as hp
from insightface.app import FaceAnalysis


def _load_model():
    session_options = onnxruntime.SessionOptions()
    session_options.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_ENABLE_ALL
    return onnxruntime.InferenceSession(
        "/tmp/wav2lip_gan.onnx",
        sess_options=session_options,
        providers=["CPUExecutionProvider"],
    )


def _detect_face(frame, detector):
    faces = detector.get(frame)
    if not faces:
        raise SystemExit("FAIL: no face detected in target video frame")

    face = max(faces, key=lambda item: float((item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1])))
    x1, y1, x2, y2 = [int(round(value)) for value in face.bbox]

    pady1, pady2, padx1, padx2 = 0, 10, 0, 0
    y1 = max(0, y1 - pady1)
    y2 = min(frame.shape[0], y2 + pady2)
    x1 = max(0, x1 - padx1)
    x2 = min(frame.shape[1], x2 + padx2)

    if x2 <= x1 or y2 <= y1:
        raise SystemExit("FAIL: detected face crop is empty")

    return frame[y1:y2, x1:x2], (y1, y2, x1, x2)


def _prepare_batch(frames, mel_batch, detector):
    img_batch = []
    frame_batch = []
    coords_batch = []

    for frame in frames:
        face, coords = _detect_face(frame, detector)
        face = cv2.resize(face, (96, 96))
        masked = face.copy()
        masked[48:, :] = 0
        img_batch.append(np.concatenate((masked, face), axis=2) / 255.0)
        frame_batch.append(frame.copy())
        coords_batch.append(coords)

    images = np.asarray(img_batch, dtype=np.float32).transpose((0, 3, 1, 2))
    mels = np.asarray(mel_batch, dtype=np.float32)
    mels = mels.reshape((len(mels), mels.shape[1], mels.shape[2], 1)).transpose((0, 3, 1, 2))
    return images, mels, frame_batch, coords_batch


def main():
    if len(sys.argv) != 4:
        raise SystemExit("Usage: lip_sync.py video_path audio_path output_path")

    video_path, audio_path, output_path = sys.argv[1:4]
    print(f"Video: {video_path}")
    print(f"Audio: {audio_path}")
    print(f"Output: {output_path}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise SystemExit(f"FAIL: could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        raise SystemExit("FAIL: target video has invalid FPS")

    wav = audio.load_wav(audio_path, hp.sample_rate)
    mel = audio.melspectrogram(wav)
    if np.isnan(mel.reshape(-1)).sum() > 0:
        raise SystemExit("FAIL: mel spectrogram contains NaN values")

    mel_step_size = 16
    mel_idx_multiplier = 80.0 / fps
    mel_chunks = []
    i = 0
    while True:
        start_idx = int(i * mel_idx_multiplier)
        if start_idx + mel_step_size > len(mel[0]):
            mel_chunks.append(mel[:, len(mel[0]) - mel_step_size:])
            break
        mel_chunks.append(mel[:, start_idx:start_idx + mel_step_size])
        i += 1

    print(f"Length of mel chunks: {len(mel_chunks)}")

    detector = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
    detector.prepare(ctx_id=-1, det_size=(640, 640))
    model = _load_model()

    silent_video = "/tmp/wav2lip_silent.mp4"
    first_frame = True
    frame_index = 0
    batch_size = 1
    writer = None

    try:
        while frame_index < len(mel_chunks):
            frames = []
            chunk_batch = mel_chunks[frame_index:frame_index + batch_size]

            for _ in chunk_batch:
                ret, frame = cap.read()
                if not ret:
                    break
                frames.append(frame)

            if not frames:
                break

            chunk_batch = chunk_batch[:len(frames)]
            images, mels, frame_batch, coords_batch = _prepare_batch(frames, chunk_batch, detector)

            if first_frame:
                h, w = frame_batch[0].shape[:2]
                writer = cv2.VideoWriter(
                    silent_video,
                    cv2.VideoWriter_fourcc(*"mp4v"),
                    fps,
                    (w, h),
                )
                if not writer.isOpened():
                    raise SystemExit("FAIL: could not open silent output video writer")
                first_frame = False

            pred = model.run(
                None,
                {"mel_spectrogram": mels, "video_frames": images},
            )[0]

            for generated, frame, coords in zip(pred, frame_batch, coords_batch):
                generated = np.clip(generated.transpose(1, 2, 0) * 255.0, 0, 255).astype(np.uint8)
                y1, y2, x1, x2 = coords
                generated = cv2.resize(generated, (x2 - x1, y2 - y1))
                frame[y1:y2, x1:x2] = generated
                writer.write(frame)

            frame_index += len(frames)
            print(f"Processed {frame_index} frames")

    finally:
        cap.release()
        if writer is not None:
            writer.release()

    if first_frame:
        raise SystemExit("FAIL: no video frames were processed")

    if not os.path.exists(silent_video) or os.path.getsize(silent_video) <= 0:
        raise SystemExit("FAIL: silent lip-sync video was not produced")

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                silent_video,
                "-i",
                audio_path,
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-shortest",
                output_path,
            ],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"FAIL: ffmpeg mux failed with exit code {exc.returncode}") from exc

    if not os.path.exists(output_path):
        raise SystemExit(f"FAIL: output file was not created: {output_path}")

    output_size = os.path.getsize(output_path)
    if output_size <= 10000:
        raise SystemExit(f"FAIL: output file is under 10000 bytes: {output_size}")

    print(f"Done: {output_path} ({output_size} bytes)")


if __name__ == "__main__":
    main()
