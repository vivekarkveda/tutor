import os
from gtts import gTTS
from io import BytesIO

def text_files_to_audio_bytes(txt_file_list, output_folder=r"C:\Vivek_Main\Manim_project\Manin_main\src\output\audiofile"):
    """
    Reads a list of .txt files, converts each file's content into audio bytes using gTTS,
    and stores each audio as an MP3 file in the output folder.
    
    Returns a list of audio bytes.
    """
    os.makedirs(output_folder, exist_ok=True)
    audio_bytes_list = []

    for idx, txt_file in enumerate(txt_file_list, 1):
        # Read the text from the file
        with open(txt_file, "r", encoding="utf-8") as f:
            text = f.read().strip()
        
        if not text:
            print(f"⚠️ Skipping empty file: {txt_file}")
            continue

        # Generate audio using gTTS
        tts = gTTS(text=text, lang='en')
        mp3_fp = BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        audio_bytes = mp3_fp.read()
        audio_bytes_list.append(audio_bytes)

        # Save MP3 file
        file_path = os.path.join(output_folder, f"audio_{idx}.mp3")
        with open(file_path, "wb") as f:
            f.write(audio_bytes)
        print(f"✅ Saved audio {idx} from {txt_file} to {file_path}")

    return audio_bytes_list
