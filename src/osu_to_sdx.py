import os
import re
import zipfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image
import audioread
from lameenc import Encoder

TRACK_MAPPINGS = {
    3: [1, 2, 3],           
    4: [1, 2, 3, 2],        
    5: [1, 2, 3, 2, 1],     
    6: [1, 2, 3, 1, 2, 3],  
    8: [1, 2, 3, 1, 2, 3, 2, 1],
    9: [1, 2, 3, 1, 2, 3, 1, 2, 3],
    10:[1, 2, 3, 1, 2, 3, 1, 2, 3, 2]
}

def detect_key_mode(osu_path):
    """Detect the key mode from the .osu file based on CircleSize."""
    with open(osu_path, 'r', encoding='utf-8') as file:
        content = file.read()
    circle_size_match = re.search(r'CircleSize:(\d+)', content)
    if circle_size_match:
        key_mode = int(circle_size_match.group(1))
        if key_mode in TRACK_MAPPINGS:
            return key_mode
    raise ValueError("Unsupported key mode or CircleSize not found.")

def convert_audio_to_mp3(input_path, output_path):
    """Convert audio file to MP3 using audioread and lameenc."""
    with audioread.audio_open(input_path) as f:
        encoder = Encoder()
        encoder.set_bit_rate(192)  
        encoder.set_channels(f.channels)
        encoder.set_sample_rate(f.samplerate)
        mp3_data = bytearray()
        for buf in f:
            mp3_data.extend(encoder.encode(buf))
        mp3_data.extend(encoder.flush())
    with open(output_path, 'wb') as f:
        f.write(mp3_data)

def convert_osu_to_sdx(osu_path, output_dir, progress_var=None):
    """Convert osu! file to .sdx format with proper BPM reset."""
    with open(osu_path, 'r', encoding='utf-8') as file:
        osu_content = file.read()

    metadata = {}
    for line in re.findall(r'(\w+):(.+)', osu_content):
        metadata[line[0].strip()] = line[1].strip()

    key_mode = detect_key_mode(osu_path)
    track_map = TRACK_MAPPINGS[key_mode]

    general_match = re.search(r'\[General\]\n(.*?)(?=\n\[)', osu_content, re.DOTALL)
    timing_points_match = re.search(r'\[TimingPoints\]\n(.*?)(?=\n\[|\Z)', osu_content, re.DOTALL)
    if not general_match or not timing_points_match:
        raise ValueError("Missing [General] or [TimingPoints] section.")
    
    general = general_match.group(1)
    timing_points = timing_points_match.group(1).strip().split('\n')
    first_timing_point = timing_points[0].split(',')
    first_bpm = 60000 / float(first_timing_point[1])
    offset = int(first_timing_point[0]) / 1000
    timing_changes = [(int(tp.split(',')[0]) / 1000, 60000 / float(tp.split(',')[1])) 
                      for tp in timing_points if float(tp.split(',')[1]) > 0]

    audio_filename = re.search(r'AudioFilename:\s*"?(.*?)"?\s*$', general, re.MULTILINE).group(1)
    audio_path = os.path.join(os.path.dirname(osu_path), audio_filename)
    audio_ext = os.path.splitext(audio_filename)[1].lower()
    if audio_ext not in ['.mp3', '.wav']:
        new_audio_path = os.path.join(output_dir, 'temp_music.mp3')
        convert_audio_to_mp3(audio_path, new_audio_path)
        audio_path = new_audio_path
    else:
        new_audio_path = None

    events_match = re.search(r'\[Events\]\n(.*?)(?=\n\[|\Z)', osu_content, re.DOTALL)
    if not events_match:
        raise ValueError("Missing [Events] section.")
    background_filename = next((e.split(',')[2].strip('"') for e in events_match.group(1).strip().split('\n') 
                               if e.startswith('0,0')), None)
    if not background_filename:
        raise ValueError("Background image not found.")

    hit_objects_match = re.search(r'\[HitObjects\]\n(.*?)(?=\n\[|\Z)', osu_content, re.DOTALL)
    if not hit_objects_match:
        raise ValueError("Missing [HitObjects] section.")
    hit_objects = hit_objects_match.group(1).strip().split('\n')

    processed_notes = []
    used_times = {}
    current_bpm = timing_changes[0][1]
    current_offset = timing_changes[0][0]  
    timing_idx = 1

    total_objects = len(hit_objects)
    for i, obj in enumerate(hit_objects):
        if progress_var:
            progress_var.set((i + 1) / total_objects * 100)

        obj_data = obj.split(',')
        x = int(obj_data[0])
        time = int(obj_data[2]) / 1000
        obj_type = int(obj_data[3])
        track = track_map[x // (512 // key_mode)]

        while timing_idx < len(timing_changes) and time >= timing_changes[timing_idx][0]:
            change_time, new_bpm = timing_changes[timing_idx]
            beat_time = (change_time - current_offset) * (current_bpm / 60)
            beat = int(beat_time)
            fraction = beat_time - beat
            denominator = 1920
            numerator = int(fraction * denominator)
            key = (beat, numerator, denominator)
            if key not in used_times:
                processed_notes.append(f"B,{beat},{numerator},{denominator},{new_bpm}")
                used_times[key] = 'B'
            current_offset = change_time
            current_bpm = new_bpm
            timing_idx += 1
            used_times.clear() 

        beat_time = (time - current_offset) * (current_bpm / 60)
        beat = int(beat_time)
        fraction = beat_time - beat
        denominator = 1920
        numerator = int(fraction * denominator)

        if obj_type & 128:  
            end_time = int(obj_data[5].split(':')[0]) / 1000
            end_beat_time = (end_time - current_offset) * (current_bpm / 60)
            end_beat = int(end_beat_time)
            end_fraction = end_beat_time - end_beat
            end_numerator = int(end_fraction * denominator)
            key = (beat, numerator, denominator)
            if key not in used_times:
                processed_notes.append(f"X,{beat},{numerator},{denominator},{track},1")
                used_times[key] = 'X'
            end_key = (end_beat, end_numerator, denominator)
            if end_key not in used_times:
                processed_notes.append(f"X,{end_beat},{end_numerator},{denominator},{track},1")
                used_times[end_key] = 'X'
        else: 
            key = (beat, numerator, denominator)
            if key not in used_times:
                processed_notes.append(f"D,{beat},{numerator},{denominator},{track},1")
                used_times[key] = 'D'

    while timing_idx < len(timing_changes):
        change_time, new_bpm = timing_changes[timing_idx]
        beat_time = (change_time - current_offset) * (current_bpm / 60)
        beat = int(beat_time)
        fraction = beat_time - beat
        denominator = 1920
        numerator = int(fraction * denominator)
        key = (beat, numerator, denominator)
        if key not in used_times:
            processed_notes.append(f"B,{beat},{numerator},{denominator},{new_bpm}")
            used_times[key] = 'B'
        current_offset = change_time
        current_bpm = new_bpm
        timing_idx += 1
        used_times.clear()

    sdx_filename = os.path.basename(osu_path).replace('.osu', '.sdx')
    sdx_path = os.path.join(output_dir, sdx_filename)
    with zipfile.ZipFile(sdx_path, 'w') as sdx_zip:
        data_sdz = f"[Meta]\ntitle = {metadata.get('Title', 'Unknown')}\n"
        data_sdz += f"author = {metadata.get('Artist', 'Unknown')}\n"
        data_sdz += f"mapper = {metadata.get('Creator', 'Unknown')}\n"
        data_sdz += "level = 5\n"
        data_sdz += f"bpm = {int(first_bpm)}\noffset = {offset}\nbg_offset = 0\n\n"
        data_sdz += "[Data]\n" + "\n".join(processed_notes)
        sdx_zip.writestr('data.sdz', data_sdz)
        sdx_zip.write(audio_path, 'music.mp3')
        bg_path = os.path.join(os.path.dirname(osu_path), background_filename)
        if not background_filename.lower().endswith('.png'):
            bg_png_path = os.path.join(output_dir, 'bg.png')
            Image.open(bg_path).save(bg_png_path)
            bg_path = bg_png_path
        sdx_zip.write(bg_path, 'bg.png')

    if new_audio_path and os.path.exists(new_audio_path):
        os.remove(new_audio_path)
    return sdx_path

def create_gui():
    """Create GUI for the converter."""
    root = tk.Tk()
    root.title("osu! to SDX Converter")
    root.geometry("400x300")
    root.resizable(False,False)

    
    osu_path_var = tk.StringVar()
    output_dir_var = tk.StringVar()
    progress_var = tk.DoubleVar()

    
    tk.Label(root, text="osu! to SDX Converter", font=("Arial", 14)).pack(pady=10)

    tk.Label(root, text="Select .osu file:").pack()
    tk.Entry(root, textvariable=osu_path_var, width=40).pack()
    tk.Button(root, text="Browse", command=lambda: osu_path_var.set(filedialog.askopenfilename(filetypes=[("osu! files", "*.osu")]))).pack()

    tk.Label(root, text="Select output directory:").pack()
    tk.Entry(root, textvariable=output_dir_var, width=40).pack()
    tk.Button(root, text="Browse", command=lambda: output_dir_var.set(filedialog.askdirectory())).pack()

    tk.Button(root, text="Convert", command=lambda: convert_button(osu_path_var.get(), output_dir_var.get(), progress_var)).pack(pady=20)

    progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100)
    progress_bar.pack(fill=tk.X, padx=20)

    root.mainloop()

def convert_button(osu_path, output_dir, progress_var):
    if not osu_path or not output_dir:
        messagebox.showwarning("Warning", "Please select both an .osu file and an output directory.")
        return
    try:
        sdx_path = convert_osu_to_sdx(osu_path, output_dir, progress_var)
        messagebox.showinfo("Success", f"Conversion completed! SDX file saved to {sdx_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Conversion failed: {str(e)}")

if __name__ == "__main__":
    create_gui()
