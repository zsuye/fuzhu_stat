import cv2
import os

def load_images_from_folder(folder):
    images = []
    for filename in sorted(os.listdir(folder)):
        if filename.endswith('.png'):
            img = cv2.imread(os.path.join(folder, filename))
            if img is not None:
                images.append(img)
    return images

def stitch_images(images):
    stitcher = cv2.Stitcher_create()
    status, panorama = stitcher.stitch(images)
    if status == cv2.Stitcher_OK:
        return panorama
    else:
        print(f"拼接失败，错误代码：{status}")
        return None

def main():
    folder = r'C:\Users\fuchu\Videos\x'
    images = load_images_from_folder(folder)
    if not images:
        print("没有找到任何图像")
        return
    
    panorama = stitch_images(images)
    if panorama is not None:
        output_file = os.path.join(folder, 'panorama.png')
        cv2.imwrite(output_file, panorama)
        print(f"全景图已保存到 {output_file}")

if __name__ == "__main__":
    main()
