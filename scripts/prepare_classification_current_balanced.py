from pathlib import Path
import random
import shutil

import cv2
import numpy as np

SRC_ROOT = Path(r"D:\05Data\visual-quality-inspection\data\train")
OUT_ROOT = Path(r"D:\05Data\visual-quality-inspection\data\classification_current_balanced")
SEED = 42
VAL_RATIO = 0.15

random.seed(SEED)
np.random.seed(SEED)


class_map = {'0': 'normal', '1': 'defect'}


def reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def copy_file_bytes(src: Path, dst: Path) -> None:
    with src.open('rb') as src_file, dst.open('wb') as dst_file:
        shutil.copyfileobj(src_file, dst_file)


def copy_files(files: list[Path], dst_dir: Path, prefix: str) -> None:
    for idx, src in enumerate(files):
        dst = dst_dir / f'{prefix}_{idx:05d}{src.suffix.lower()}'
        copy_file_bytes(src, dst)


def random_augment(image: np.ndarray) -> np.ndarray:
    h, w = image.shape[:2]
    out = image.copy()

    if random.random() < 0.85:
        alpha = random.uniform(0.78, 1.22)
        beta = random.randint(-18, 18)
        out = cv2.convertScaleAbs(out, alpha=alpha, beta=beta)

    if random.random() < 0.55:
        gamma = random.uniform(0.85, 1.18)
        lut = np.array([((i / 255.0) ** (1.0 / gamma)) * 255 for i in range(256)]).astype('uint8')
        out = cv2.LUT(out, lut)

    if random.random() < 0.7:
        angle = random.uniform(-8, 8)
        scale = random.uniform(0.94, 1.06)
        tx = random.uniform(-0.05, 0.05) * w
        ty = random.uniform(-0.05, 0.05) * h
        matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, scale)
        matrix[0, 2] += tx
        matrix[1, 2] += ty
        out = cv2.warpAffine(out, matrix, (w, h), borderMode=cv2.BORDER_REFLECT101)

    if random.random() < 0.35:
        out = cv2.flip(out, 1)

    if random.random() < 0.35:
        ksize = random.choice([3, 5])
        out = cv2.GaussianBlur(out, (ksize, ksize), 0)

    if random.random() < 0.45:
        noise = np.random.normal(0, random.uniform(2.5, 8.0), out.shape).astype(np.float32)
        out = np.clip(out.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    if random.random() < 0.28:
        sharpen = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
        out = cv2.filter2D(out, -1, sharpen)

    if random.random() < 0.2:
        cut_w = max(6, int(w * random.uniform(0.04, 0.1)))
        cut_h = max(6, int(h * random.uniform(0.04, 0.1)))
        x1 = random.randint(0, max(0, w - cut_w))
        y1 = random.randint(0, max(0, h - cut_h))
        out[y1:y1 + cut_h, x1:x1 + cut_w] = int(out.mean())

    return out


def load_images(paths: list[Path]) -> list[np.ndarray]:
    images = []
    for path in paths:
        image = cv2.imread(str(path))
        if image is not None:
            images.append(image)
    return images


def main() -> None:
    files_by_class = {}
    for src_name in class_map:
        files = [p for p in (SRC_ROOT / src_name).iterdir() if p.is_file()]
        random.shuffle(files)
        files_by_class[src_name] = files

    normal_files = files_by_class['0']
    defect_files = files_by_class['1']
    if not normal_files or not defect_files:
        raise SystemExit('训练数据不能为空。')

    val_count = max(1, int(len(normal_files) * VAL_RATIO))
    val_normal = normal_files[:val_count]
    train_normal = normal_files[val_count:]

    val_defect = defect_files[:val_count]
    train_defect = defect_files[val_count:]

    for split in ['train', 'val']:
        for cls in class_map.values():
            reset_dir(OUT_ROOT / split / cls)

    copy_files(train_defect, OUT_ROOT / 'train' / 'defect', 'defect')
    copy_files(val_defect, OUT_ROOT / 'val' / 'defect', 'defect')
    copy_files(train_normal, OUT_ROOT / 'train' / 'normal', 'normal_orig')
    copy_files(val_normal, OUT_ROOT / 'val' / 'normal', 'normal_val')

    train_target = len(train_defect)
    current_train_normal = len(list((OUT_ROOT / 'train' / 'normal').iterdir()))
    normal_sources = load_images(train_normal)
    if not normal_sources:
        raise SystemExit('正常类训练图像读取失败。')

    for idx in range(current_train_normal, train_target):
        base = normal_sources[idx % len(normal_sources)]
        aug = random_augment(base)
        out_path = OUT_ROOT / 'train' / 'normal' / f'normal_aug_{idx:05d}.jpg'
        cv2.imwrite(str(out_path), aug)

    print('train_defect=', len(list((OUT_ROOT / 'train' / 'defect').iterdir())))
    print('train_normal=', len(list((OUT_ROOT / 'train' / 'normal').iterdir())))
    print('val_defect=', len(list((OUT_ROOT / 'val' / 'defect').iterdir())))
    print('val_normal=', len(list((OUT_ROOT / 'val' / 'normal').iterdir())))


if __name__ == '__main__':
    main()
