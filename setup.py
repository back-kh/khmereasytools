
from pathlib import Path
from setuptools import setup, find_packages

with (Path(__file__).parent / "README.md").open(encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="khmereasytools",
    version="0.5.0.dev0",
    author="Nimol Thuon",
    author_email="nimol.thuon@gmail.com",
    description="Lightweight Khmer text, local search, optional translation, and image/PDF OCR tools.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/back-kh/khmereasytools",
    project_urls={
        "Source": "https://github.com/back-kh/khmereasytools",
        "Issues": "https://github.com/back-kh/khmereasytools/issues",
        "Changelog": "https://github.com/back-kh/khmereasytools/blob/main/CHANGELOG.md",
    },
    packages=find_packages(include=["khmereasytools", "khmereasytools.*"]),
    package_data={"khmereasytools": ["data/*.txt", "data/*.json"]},
    entry_points={"console_scripts": ["khmereasytools=khmereasytools.cli:main"]},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Text Processing :: Linguistic",
    ],
    python_requires='>=3.6',
    install_requires=[], # No hard dependencies for core functions
    extras_require={
        "ocr": ["pytesseract>=0.3.8", "Pillow>=9.0.0", "pypdfium2>=4,<6"],
        "khmernltk": ["khmer-nltk>=1.6,<2"],
        "all": [
            "pytesseract>=0.3.8", "Pillow>=9.0.0", "pypdfium2>=4,<6",
            "khmer-nltk>=1.6,<2"
        ]
    }
)
