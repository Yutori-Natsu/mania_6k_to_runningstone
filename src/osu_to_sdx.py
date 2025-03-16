import os
import re
import zipfile
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image

def convert_osu_to_sdx(osu_path, output_dir):
    with open(osu_path, 'r', encoding='utf-8') as file:
        osu_content = file.read()
    metadata = {}
    for line in re.findall(r'(\w+):(.+)', osu_content):
        key, value = line
        metadata[key.strip()] = value.strip()
    general_match = re.search(r'\[General\]\n(.*?)(?=\n\[)', osu_content, re.DOTALL)
    timing_points_match = re.search(r'\[TimingPoints\]\n(.*?)(?=\n\[|\Z)', osu_content, re.DOTALL)
    if not general_match or not timing_points_match:
        messagebox.showerror("Error", "Invalid osu! file format: Missing [General] or [TimingPoints] section.")
        return
    general = general_match.group(1)
    timing_points = timing_points_match.group(1).strip().split('\n')
    first_timing_point = timing_points[0].split(',')
    first_bpm = 60000 / float(first_timing_point[1])
    offset = int(first_timing_point[0]) / 1000
    timing_changes = []
    for tp in timing_points:
        tp_data = tp.split(',')
        time = int(tp_data[0]) / 1000
        bpm = 60000 / float(tp_data[1]) if float(tp_data[1]) > 0 else None 
        if bpm:
            timing_changes.append((time, bpm))

    audio_filename_match = re.search(r'AudioFilename:\s*"?(.*?)"?\s*$', general, re.MULTILINE)
    if not audio_filename_match:
        messagebox.showerror("Error", "AudioFilename not found in [General] section.")
        return
    audio_filename = audio_filename_match.group(1)
    events_match = re.search(r'\[Events\]\n(.*?)(?=\n\[|\Z)', osu_content, re.DOTALL)
    if not events_match:
        messagebox.showerror("Error", "Invalid osu! file format: Missing [Events] section.")
        return
    events = events_match.group(1).strip().split('\n')
    background_filename = None
    for event in events:
        event_data = event.split(',')
        if event_data[0] == "0" and event_data[1] == "0": 
            background_filename = event_data[2].strip('"')
            break
    if not background_filename:
        messagebox.showerror("Error", "Background image not found in [Events] section.")
        return
    hit_objects_match = re.search(r'\[HitObjects\]\n(.*?)(?=\n\[|\Z)', osu_content, re.DOTALL)
    if not hit_objects_match:
        messagebox.showerror("Error", "Invalid osu! file format: Missing [HitObjects] section.")
        return
    hit_objects = hit_objects_match.group(1).strip().split('\n')
    processed_notes = []
    used_times = {} 
    current_bpm = timing_changes[0][1] if timing_changes else 120
    current_offset = offset
    for obj in hit_objects:
        obj_data = obj.split(',')
        x = int(obj_data[0])
        y = int(obj_data[1])
        time = int(obj_data[2]) / 1000 
        obj_type = int(obj_data[3])
        track = (x // 128) + 1
        if track == 4:
            track = 2
        while timing_changes and time >= timing_changes[0][0]:
            change_time, new_bpm = timing_changes.pop(0)
            beat_time = (change_time - current_offset) * (current_bpm / 60)
            beat = int(beat_time)
            fraction = beat_time - beat
            denominator = 1920  # 使用 1920 作为分母
            numerator = int(fraction * denominator)

            # 插入 BPM 变化音符
            bpm_change_key = (beat, numerator, denominator)
            if bpm_change_key not in used_times:
                processed_notes.append(f"B,{beat},{numerator},{denominator},{new_bpm}")
                used_times[bpm_change_key] = 'B'

            # 更新当前 BPM 和 offset
            current_offset = change_time
            current_bpm = new_bpm
        beat_time = (time - current_offset) * (current_bpm / 60)
        beat = int(beat_time)
        fraction = beat_time - beat
        denominator = 1920  
        numerator = int(fraction * denominator)
        if obj_type & 128:  
            aaa=obj_data[5].split(':')
            end_time = int(aaa[0]) / 1000 
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
    sdx_filename = os.path.basename(osu_path).replace('.osu', '.sdx')
    sdx_path = os.path.join(output_dir, sdx_filename)
    with zipfile.ZipFile(sdx_path, 'w') as sdx_zip:
        data_sdz = f"[Meta]\n"
        data_sdz += f"title = {metadata.get('Title', 'Unknown')}\n"
        data_sdz += f"author = {metadata.get('Artist', 'Unknown')}\n"
        data_sdz += f"mapper = {metadata.get('Creator', 'Unknown')}\n"
        data_sdz += f"level = 5\n"  
        data_sdz += f"bpm = {int(first_bpm)}\n"
        data_sdz += f"offset = {offset}\n"
        data_sdz += f"bg_offset = 0\n\n"
        data_sdz += "[Data]\n" + "\n".join(processed_notes)
        sdx_zip.writestr('data.sdz', data_sdz)
        audio_path = os.path.join(os.path.dirname(osu_path), audio_filename)
        sdx_zip.write(audio_path, 'music.mp3')
        bg_path = os.path.join(os.path.dirname(osu_path), background_filename)
        if not background_filename.lower().endswith('.png'):
            bg_png_path = os.path.join(os.path.dirname(osu_path), os.path.splitext(background_filename)[0] + '.png')
            Image.open(bg_path).save(bg_png_path)
            bg_path = bg_png_path
        sdx_zip.write(bg_path, 'bg.png')
    messagebox.showinfo("Success", f"Conversion completed! SDX file saved to {sdx_path}")

def main():
    root = tk.Tk()
    root.withdraw()
    osu_path = filedialog.askopenfilename(title="Select osu! Mania 4K .osu file", filetypes=[("osu! files", "*.osu")])
    if not osu_path:
        messagebox.showinfo("Info", "No file selected. Exiting.")
        return
    output_dir = filedialog.askdirectory(title="Select output directory")
    if not output_dir:
        messagebox.showinfo("Info", "No output directory selected. Exiting.")
        return
    convert_osu_to_sdx(osu_path, output_dir)

if __name__ == "__main__":
    main()
