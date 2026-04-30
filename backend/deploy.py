"""Build ``lambda-deployment.zip`` for Terraform (no Docker; uses uv Linux wheels)."""

from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "lambda-package"
ZIP_PATH = ROOT / "lambda-deployment.zip"
REQ_EXPORT = ROOT / ".lambda_requirements_export.txt"


def main() -> None:
    print("Creating Lambda deployment package...")

    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True)
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    print("Installing dependencies for Lambda runtime (linux/amd64 via uv)...")
    subprocess.run(
        [
            "uv",
            "export",
            "--no-dev",
            "--no-hashes",
            "--format",
            "requirements-txt",
            "-o",
            str(REQ_EXPORT),
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            "3.12",
            "--python-platform",
            "x86_64-manylinux2014",
            "-r",
            str(REQ_EXPORT),
            "--target",
            str(BUILD),
        ],
        cwd=ROOT,
        check=True,
    )

    print("Copying application files...")
    shutil.copytree(ROOT / "app", BUILD / "app")
    shutil.copy2(ROOT / "lambda_handler.py", BUILD / "lambda_handler.py")

    print("Creating zip file...")
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in BUILD.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(BUILD).as_posix())

    size_mb = ZIP_PATH.stat().st_size / (1024 * 1024)
    print(f"Created lambda-deployment.zip ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
