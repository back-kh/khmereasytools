#!/usr/bin/env python3
"""
A Python script to parse Khmer text from an HTML file using BeautifulSoup,
and save the extracted text to a `.txt` file with the same base name.

Usage:
    python khmer_html_parser.py path/to/input.html

Dependencies:
    - BeautifulSoup4
      Install via pip:
          pip install -r requirements.txt

Author:
    Nimol Thuon (https://github.com/back-kh)
"""

import os
import sys
import argparse
from bs4 import BeautifulSoup


def parse_khmer_html(html_content: str) -> str:
    """
    Extracts and cleans text from Khmer HTML content.

    :param html_content: The raw HTML content as a string.
    :return: The extracted text, with extra whitespace removed.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    # Extract raw text with spaces as separators
    text = soup.get_text(separator=' ')
    # Remove extra whitespace and normalize spaces
    cleaned_text = ' '.join(text.split())
    return cleaned_text


def read_html_file(file_path: str) -> str:
    """
    Reads the contents of an HTML file.

    :param file_path: Path to the HTML file.
    :return: A string containing the HTML content.
    :raises FileNotFoundError: If the specified file does not exist.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Input file not found: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()


def write_to_text_file(file_path: str, text: str) -> None:
    """
    Writes text to a specified file.

    :param file_path: The path to the output `.txt` file.
    :param text: The text content to write.
    """
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(text)


def generate_output_path(input_path: str) -> str:
    """
    Generates the output `.txt` file path based on the input HTML file path.

    :param input_path: Path to the input HTML file.
    :return: Path to the output `.txt` file.
    """
    base, _ = os.path.splitext(input_path)
    return f"{base}.txt"


def main():
    """
    Main function to execute the parsing and saving process.
    """
    parser = argparse.ArgumentParser(
        description="Parse and extract Khmer text from an HTML file."
    )
    parser.add_argument(
        "input_file",
        help="Path to the input HTML file."
    )

    args = parser.parse_args()

    input_path = args.input_file
    output_path = generate_output_path(input_path)

    try:
        # Read HTML content from the input file
        html_content = read_html_file(input_path)
        print(f"[INFO] Successfully read HTML file: {input_path}")

        # Parse Khmer text from the HTML content
        extracted_text = parse_khmer_html(html_content)
        print("[INFO] Successfully extracted Khmer text from HTML.")

        # Write the extracted text to the output file
        write_to_text_file(output_path, extracted_text)
        print(f"[INFO] Extracted text saved to: {output_path}")

    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
        main()

