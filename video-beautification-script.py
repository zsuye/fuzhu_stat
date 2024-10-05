import cv2
import numpy as np
import dlib
import concurrent.futures
import time

def apply_skin_smoothing(frame, strength=0.5):
    if frame.size == 0:
        return frame
    blurred = cv2.GaussianBlur(frame, (21, 21), 0)
    return cv2.addWeighted(frame, 1 - strength, blurred, strength, 0)

def apply_brightness(frame, value=30):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    v = cv2.add(v, value)
    final_hsv = cv2.merge((h, s, v))
    return cv2.cvtColor(final_hsv, cv2.COLOR_HSV2BGR)

def process_frame(frame, detector):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = detector(gray)
    for face in faces:
        if face.left() < face.right() and face.top() < face.bottom():
            face_region = frame[face.top():face.bottom(), face.left():face.right()]
            if face_region.size > 0:
                face_region = apply_skin_smoothing(face_region)
                frame[face.top():face.bottom(), face.left():face.right()] = face_region
    frame = apply_brightness(frame)
    return frame

def beautify_video(input_path, output_path):
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print(f"错误：无法打开视频文件 {input_path}")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    detector = dlib.get_frontal_face_detector()

    frame_count = 0
    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            future = executor.submit(process_frame, frame, detector)
            futures.append(future)

            if len(futures) > 10:  # 限制并发任务数量
                done, _ = concurrent.futures.wait(futures, return_when=concurrent.futures.FIRST_COMPLETED)
                for future in done:
                    processed_frame = future.result()
                    out.write(processed_frame)
                    frame_count += 1
                    futures.remove(future)

                    if frame_count % 30 == 0:  # 每30帧更新一次进度
                        elapsed_time = time.time() - start_time
                        progress = frame_count / total_frames * 100
                        print(f"进度: {progress:.2f}%, 已处理 {frame_count} 帧, 用时 {elapsed_time:.2f} 秒")

        # 处理剩余的帧
        for future in concurrent.futures.as_completed(futures):
            processed_frame = future.result()
            out.write(processed_frame)
            frame_count += 1

    cap.release()
    out.release()
    cv2.destroyAllWindows()

    total_time = time.time() - start_time
    print(f"处理完成！总用时: {total_time:.2f} 秒, 总共处理 {frame_count} 帧")

# 使用示例
input_video = "C:/Users/fuchu/Videos/未命名.mp4"
output_video = "output_multithread.mp4"
beautify_video(input_video, output_video)