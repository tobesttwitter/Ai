import sys
import os
import cv2
import insightface
from insightface.app import FaceAnalysis

def main():
    source_path, target_path, output_path = sys.argv[1], sys.argv[2], sys.argv[3]
    print(f"Source: {source_path}")
    print(f"Target: {target_path}")
    print(f"Output: {output_path}")

    app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
    app.prepare(ctx_id=-1, det_size=(640, 640))
    swapper = insightface.model_zoo.get_model(
        'inswapper_128.onnx',
        providers=['CPUExecutionProvider'],
    )

    src_img = cv2.imread(source_path)
    if src_img is None:
        raise SystemExit(f"Could not read source image: {source_path}")
    src_faces = app.get(src_img)
    if not src_faces:
        raise SystemExit("No face found in source image")
    src_face = src_faces[0]

    cap = cv2.VideoCapture(target_path)
    if not cap.isOpened():
        raise SystemExit(f"Could not open target video: {target_path}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))

    frame_count = 0
    frames_with_faces = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        faces = app.get(frame)
        if faces:
            frames_with_faces += 1
        for face in faces:
            frame = swapper.get(frame, face, src_face, paste_back=True)
        out.write(frame)
        frame_count += 1
        if frame_count % 30 == 0:
            print(f"Processed {frame_count} frames")

    cap.release()
    out.release()

    if frames_with_faces == 0:
        raise SystemExit("FAIL: no faces detected in any frame of the target video")
    output_size = os.path.getsize(output_path)
    if output_size < 10000:
        raise SystemExit(f"FAIL: output file is under 10000 bytes: {output_size}")
    print(f"Done: {output_path} ({frame_count} frames, {frames_with_faces} frames with faces, {output_size} bytes)")

if __name__ == '__main__':
    main()
