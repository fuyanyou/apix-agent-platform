from pathlib import Path
from typing import Tuple
import base64
import os
import yaml
from apix_agent.commons.logger import logger

# ==========================================================
# Yaml
# ==========================================================
#将yaml文件加载为字典，并可选择返回特定的键值，便于配置管理和数据存储。
def load_from_yaml(dir, key=None) -> dict | str:
    """
    Load yaml file and optionally return a specific key.

    Args:
        dir (str): Path to yaml file.
        key (str, optional): Specific key to retrieve from yaml content.
            If provided, return config[key], otherwise return full config.

    Returns:
        dict | str:
            - Full yaml data (dict) if key is None
            - Value of the specified key if key is provided (may be None if key not found)

    Raises:
        Exception: If file reading or yaml parsing fails.
    """
    config = None
    try:
        if os.path.exists(dir):
            with open(dir, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        else:
            config = {}
        if key is not None:
            return config.get(key)
    
    except Exception as e:
        logger.error(f"Error loading yaml file: {e}")
        raise
    return config

#将字典数据写入yaml文件（覆盖模式），便于配置管理和数据存储。
def write_to_yaml(dir, data: dict):
    """
    Write data to yaml file (overwrite mode).

    Args:
        dir (str): Path to yaml file.
        data (dict): Data to be written into yaml.

    Returns:
        None

    Raises:
        Exception: If file writing fails.
    """
    try:
        if not os.path.exists(dir):
            Path(dir).parent.mkdir(parents=True, exist_ok=True)
        with open(dir, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True)
    except Exception as e:
        logger.error(f"Error writing to yaml file: {e}")
        raise

#将字典数据追加（合并）到yaml文件中，如果文件存在则加载现有数据并与新数据合并
# ，如果文件不存在则创建新文件，便于配置管理和数据存储。
def append_to_yaml(dir, new_data: dict):
    """
    Append (merge) data into yaml file.

    If file exists:
        - Load existing yaml data
        - Merge with new_data using dict.update()
    If file does not exist:
        - Create a new yaml file with new_data

    Args:
        dir (str): Path to yaml file.
        new_data (dict): New data to merge into existing yaml.

    Returns:
        None

    Raises:
        Exception: If file read/write or yaml parsing fails.
    """
    try:
        if os.path.exists(dir):
            with open(dir, "r", encoding="utf-8") as f:
                existing_data = yaml.safe_load(f) or {}
        else:
            existing_data = {}

        # Update existing data with new data
        existing_data.update(new_data)

        with open(dir, "w", encoding="utf-8") as f:
            yaml.safe_dump(existing_data, f, allow_unicode=True)
    except Exception as e:
        logger.error(f"Error appending to yaml file: {e}")
        raise
#将特定的键值对更新到yaml文件中，如果内容为空则删除该键，便于配置管理和数据存储。
def update_to_yaml(file_path: Path, title: str, content: str) -> dict:
    """
    Update or delete a key in yaml file.

    Args:
        file_path (Path): yaml file path
        title (str): memo title
        content (str): memo content, if empty -> delete

    Returns:
        dict: latest full yaml data
    """
    try:
        # Load existing data
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}

        if not content.strip():
            # Delete
            if title in data:
                del data[title]
        else:
            # Insert / Update
            data[title] = content

        # Write back
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True)

        return data

    except Exception as e:
        logger.error(f"Error updating to yaml file: {e}")
        raise

# ==========================================================
# Image
# ==========================================================
#将图片文件转换为base64字符串，并返回对应的MIME类型，便于在网络传输和数据存储中使用。
def image_to_base64(image_path: str) -> Tuple[str, str]:
    """
    Convert an image file to base64 string.

    Supported formats:
        .png, .jpg, .jpeg, .gif, .bmp, .webp

    Returns:
        (base64_string, mime_type)
    """

    allowed_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".webp": "image/webp",
    }

    ext = os.path.splitext(image_path)[1].lower()

    if ext not in allowed_types:
        raise ValueError(f"Unsupported image type: {ext}")

    mime_type = allowed_types[ext]

    try:
        # Read image as binary
        with open(image_path, "rb") as f:
            data = f.read()

        # Encode to base64
        base64_str = base64.b64encode(data).decode("utf-8")

        return base64_str, mime_type

    except Exception as e:
        raise e


# ==========================================================
# Audio
# ==========================================================
#将音频文件转换为base64字符串，并返回对应的MIME类型，便于在网络传输和数据存储中使用。
def audio_to_base64(audio_path: str) -> Tuple[str, str]:
    """
    Convert an audio file to base64 string.

    Supported formats:
        .mp3, .wav, .ogg, .m4a, .aac, .flac

    Returns:
        (base64_string, mime_type)
    """

    allowed_types = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".flac": "audio/flac",
    }

    ext = os.path.splitext(audio_path)[1].lower()

    if ext not in allowed_types:
        raise ValueError(f"Unsupported audio type: {ext}")

    mime_type = allowed_types[ext]

    try:
        # Read audio as binary
        with open(audio_path, "rb") as f:
            data = f.read()

        # Encode to base64
        base64_str = base64.b64encode(data).decode("utf-8")

        return base64_str, mime_type

    except Exception as e:
        raise e


# ==========================================================
# Video
# ==========================================================
#将视频文件转换为base64字符串，并返回对应的MIME类型，便于在网络传输和数据存储中使用。
def video_to_base64(video_path: str) -> Tuple[str, str]:
    """
    Convert a video file to base64 string.

    Supported formats:
        .mp4, .webm, .mov, .avi, .mkv

    Returns:
        (base64_string, mime_type)
    """

    allowed_types = {
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".mov": "video/quicktime",
        ".avi": "video/x-msvideo",
        ".mkv": "video/x-matroska",
    }

    ext = os.path.splitext(video_path)[1].lower()

    if ext not in allowed_types:
        raise ValueError(f"Unsupported video type: {ext}")

    mime_type = allowed_types[ext]

    try:
        # Read video as binary
        with open(video_path, "rb") as f:
            data = f.read()

        # Encode to base64
        base64_str = base64.b64encode(data).decode("utf-8")

        return base64_str, mime_type

    except Exception as e:
        raise e
    
# ==========================================================
# Text Loader
# ==========================================================
#将文本文件加载为字符串，并支持多种常见文本格式，便于在应用中处理和显示文本内容。
def load_text(file_path: str) -> str:
    """
    Load text content from a supported text file.

    Supported formats:
        .txt, .md, .log, .json, .csv,
        .xml, .html, .htm,
        .py, .js, .ts,
        .yaml, .yml

    Returns:
        file content as string

    Raises:
        ValueError: if file extension is not supported
        Exception: if file reading fails
    """

    allowed_types = {
        ".txt",
        ".md",
        ".log",
        ".json",
        ".csv",
        ".xml",
        ".html",
        ".htm",
        ".py",
        ".js",
        ".ts",
        ".yaml",
        ".yml",
    }

    ext = os.path.splitext(file_path)[1].lower()

    if ext not in allowed_types:
        raise ValueError(f"Unsupported text file type: {ext}")

    try:
        # Try reading with utf-8
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    except UnicodeDecodeError:
        # Fallback for files with BOM
        with open(file_path, "r", encoding="utf-8-sig") as f:
            return f.read()

    except Exception as e:
        raise e
    
