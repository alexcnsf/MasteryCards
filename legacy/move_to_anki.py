import os
import shutil
import platform

def get_anki_media_folder():
    """Determine the path to Anki's media folder based on the OS."""
    user_folder = "User 1"  # Replace with your Anki profile name if it's not "User 1"
    if platform.system() == "Darwin":  # macOS
        return os.path.expanduser(f"~/Library/Application Support/Anki2/{user_folder}/collection.media")
    elif platform.system() == "Windows":  # Windows
        return os.path.expandvars(f"%APPDATA%\\Anki2\\{user_folder}\\collection.media")
    elif platform.system() == "Linux":  # Linux
        return os.path.expanduser(f"~/.local/share/Anki2/{user_folder}/collection.media")
    else:
        raise Exception("Unsupported operating system.")

def move_images_to_anki(source_folder):
    """Move PNG images from the source folder to Anki's media folder."""
    anki_media_folder = get_anki_media_folder()
    if not os.path.exists(anki_media_folder):
        raise FileNotFoundError(f"Anki media folder not found at {anki_media_folder}")
    
    # Ensure the source folder exists
    if not os.path.exists(source_folder):
        raise FileNotFoundError(f"Source folder not found at {source_folder}")
    
    # Move PNG files to Anki's media folder
    for filename in os.listdir(source_folder):
        if filename.endswith(".png"):
            source_path = os.path.join(source_folder, filename)
            destination_path = os.path.join(anki_media_folder, filename)
            shutil.move(source_path, destination_path)
            print(f"Moved: {filename} to {anki_media_folder}")

# Define the folder where your PNG files are currently stored
source_folder = "anki_media"  # Replace with the folder where your images are saved

# Run the function
try:
    move_images_to_anki(source_folder)
    print("All images have been successfully moved to Anki's media folder.")
except Exception as e:
    print(f"Error: {e}")

