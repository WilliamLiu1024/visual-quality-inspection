from pathlib import Path
import random
import shutil

SRC_ROOT = Path(r"D:\05Data\visual-quality-inspection\data\train")
OUT_ROOT = Path(r"D:\05Data\visual-quality-inspection\data\classification_current")
SEED = 42
VAL_RATIO = 0.15

random.seed(SEED)


def reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def copy_split(files: list[Path], dst_dir: Path, prefix: str) -> None:
    for idx, src in enumerate(files):
        dst = dst_dir / f"{prefix}_{idx:05d}{src.suffix.lower()}"
        with src.open("rb") as src_file, dst.open("wb") as dst_file:
            shutil.copyfileobj(src_file, dst_file)


def main() -> None:
    class_map = {"0": "normal", "1": "defect"}

    for split in ["train", "val"]:
        for cls in class_map.values():
            reset_dir(OUT_ROOT / split / cls)

    for src_name, dst_name in class_map.items():
        files = [p for p in (SRC_ROOT / src_name).iterdir() if p.is_file()]
        random.shuffle(files)
        val_count = max(1, int(len(files) * VAL_RATIO))
        val_files = files[:val_count]
        train_files = files[val_count:]

        copy_split(train_files, OUT_ROOT / "train" / dst_name, dst_name)
        copy_split(val_files, OUT_ROOT / "val" / dst_name, dst_name)

        print(f"{dst_name}: total={len(files)} train={len(train_files)} val={len(val_files)}")


if __name__ == "__main__":
    main()
