import os

# Get the absolute path to the project root
# This file is in handwriting_synthesis/, so go up one level to get to project root
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_dir)

BASE_PATH = os.path.join(_project_root, "model")
BASE_DATA_PATH = "data"

data_path: str = os.path.join(BASE_PATH, BASE_DATA_PATH)
processed_data_path: str = os.path.join(data_path, "processed")
raw_data_path: str = os.path.join(data_path, "raw")
ascii_data_path: str = os.path.join(raw_data_path, "ascii")

checkpoint_path: str = os.path.join(BASE_PATH, "checkpoint")
prediction_path: str = os.path.join(BASE_PATH, "prediction")
style_path: str = os.path.join(BASE_PATH, "style")
