from pathlib import Path
MAGIC={"image":[(b"\xff\xd8\xff",".jpg"),(b"\x89PNG\r\n\x1a\n",".png"),(b"RIFF",".webp")],"video":[(b"\x00\x00\x00",".mp4"),(b"RIFF",".webm"),(b"\x1a\x45\xdf\xa3",".mkv")],"audio":[(b"ID3",".mp3"),(b"RIFF",".wav"),(b"\xff\xfb",".mp3"),(b"\xff\xf3",".mp3"),(b"\xff\xf2",".mp3")]}
def validate_upload(filename,data,kind,max_bytes):
    if len(data)>max_bytes: raise ValueError(f"{kind} exceeds the configured upload limit")
    if Path(filename).suffix.lower() not in {s for _,s in MAGIC[kind]}: raise ValueError(f"unsupported {kind} file type")
    if not any(data.startswith(sig) for sig,_ in MAGIC[kind]): raise ValueError(f"{kind} file signature is invalid")
