
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="khmereasytools",
    version="0.3.8",
    author="Nimol Thuon",
    author_email="nimol.thuon@gmail.com",
    description="A simple, self-contained library for Khmer text processing, with optional OCR and POS tagging support.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/back-kh/khmereasytools",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Text Processing :: Linguistic",
    ],
    python_requires='>=3.6',
    install_requires=[], # No hard dependencies for core functions
    extras_require={
        "ocr": ["pytesseract>=0.3.8", "Pillow>=9.0.0"],
        "khmernltk": ["khmernltk>=1.6"],
        "all": [
            "pytesseract>=0.3.8", "Pillow>=9.0.0",
            "khmernltk>=1.6"
        ]
    }
)
