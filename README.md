# osu! Mania to SDX Converter

## Description
This script converts osu! Mania 4K beatmaps to the SDX format. It processes the osu! `.osu` file, extracts relevant metadata, audio, and background images, and converts the timing and hit objects accordingly.

## Features
- Converts osu! Mania 4K beatmaps to SDX format.
- Handles LN (Long Notes) and normal notes.
- Ensures correct timing conversion using BPM and offset.
- Supports background image and audio file extraction.

## Requirements
- Python 3.x
- `Pillow` library for image processing (`pip install pillow`)
- `tkinter` for file dialogs (usually included with Python)

## Usage
1. Place the script in the same directory as your `.osu` file.
2. Run the script using Python.
3. Select the `.osu` file and choose an output directory.
4. The script will generate an `.sdx` file in the specified directory.

## Installation
1. Clone the repository or download the script file.
2. Install the required libraries:
   ```bash
   pip install pillow
   ```

## License
This project is licensed under the MIT License. See the [LICENSE](https://github.com/yukoimi/mania_to_runningstone/blob/main/LICENSE) file for details.
