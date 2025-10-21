import os

# Get the directory containing this config file (handwriting_synthesis/)
_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
# Get the project root directory (one level up from handwriting_synthesis/)
_PROJECT_ROOT = os.path.dirname(_CONFIG_DIR)

BASE_PATH = os.path.join(_PROJECT_ROOT, "model")
BASE_DATA_PATH = "data"

data_path: str = os.path.join(BASE_PATH, BASE_DATA_PATH)
processed_data_path: str = os.path.join(data_path, "processed")
raw_data_path: str = os.path.join(data_path, "raw")
ascii_data_path: str = os.path.join(raw_data_path, "ascii")

checkpoint_path: str = os.path.join(BASE_PATH, "checkpoint")
prediction_path: str = os.path.join(BASE_PATH, "prediction")
style_path: str = os.path.join(BASE_PATH, "style")
