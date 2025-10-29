## Model Training Instructions

This guide explains how to train a custom handwriting model for WriteBot using the IAM On-Line Handwriting Database.

> **Note**: Pre-trained models are included with WriteBot. You only need to follow these instructions if you want to train a custom model.

### Prerequisites

- Python 3.8+ with TensorFlow 2.12
- At least 8GB RAM
- GPU recommended (training takes ~2 days on a Tesla K80, longer on CPU)
- 10GB+ free disk space for dataset

### Step 1: Download the Dataset

The model is trained on the IAM On-Line Handwriting Database. You need to:

1. **Register for access** at http://www.fki.inf.unibe.ch/databases/iam-on-line-handwriting-database
2. **Download these files**:
   - `ascii-all.tar.gz` - Text transcriptions
   - `lineStrokes-all.tar.gz` - Stroke data  
   - `original-xml-part.tar.gz` - XML metadata

Direct download links (requires registration):
- https://fki.tic.heia-fr.ch/DBs/iamOnDB/data/ascii-all.tar.gz
- https://fki.tic.heia-fr.ch/DBs/iamOnDB/data/lineStrokes-all.tar.gz
- https://fki.tic.heia-fr.ch/DBs/iamOnDB/data/original-xml-part.tar.gz

### Step 2: Prepare the Data Directory

Extract and organize the downloaded files into this directory structure:

```
model/
├── data/
│   ├── raw/
│   │   ├── ascii/          # Extracted from ascii-all.tar.gz
│   │   ├── lineStrokes/    # Extracted from lineStrokes-all.tar.gz
│   │   └── original/       # Extracted from original-xml-part.tar.gz
│   └── blacklist.npy       # List of corrupted samples (provided)
└── README.md (this file)
```

**Commands to extract:**
```bash
cd model
mkdir -p data/raw
tar -xzf ascii-all.tar.gz -C data/raw/
tar -xzf lineStrokes-all.tar.gz -C data/raw/
tar -xzf original-xml-part.tar.gz -C data/raw/
```

### Step 3: Prepare Training Data

Run the data preparation script to process the raw data:

```python
from handwriting_synthesis.training.preparation import prepare
prepare()
```

This will:
- Parse the raw dataset files
- Filter out blacklisted samples
- Convert to numpy format for training
- Save processed data in `model/data/`

**Expected output:**
- `strokes.npy` - Stroke data
- `texts.npy` - Text transcriptions
- Processing takes 10-30 minutes

### Step 4: Train the Model

Start the training process:

```python
from handwriting_synthesis.training import train
train()
```

**Training parameters:**
- Epochs: Configurable (default: 100)
- Batch size: Configurable (default: 32)
- Learning rate: Configurable with decay

**Training time:**
- GPU (Tesla K80): ~2 days
- GPU (modern GPU): ~12-24 hours
- CPU: Not recommended (weeks)

**What happens during training:**
- Model checkpoints saved periodically
- Training metrics logged
- Validation performed each epoch
- Best model saved based on validation loss

### Step 5: Evaluate the Model

After training, test the model:

```python
from handwriting_synthesis import Hand
hand = Hand()
lines = hand.write("Test your new model here!")
```

## Training Configuration

Customize training by modifying parameters in `handwriting_synthesis/training/train.py`:

```python
BATCH_SIZE = 32
LEARNING_RATE = 0.001
NUM_EPOCHS = 100
VALIDATION_SPLIT = 0.1
```

## Troubleshooting

### Out of Memory Errors
- Reduce batch size
- Use a machine with more RAM
- Use gradient accumulation

### Poor Quality Output
- Train for more epochs
- Increase dataset size
- Adjust learning rate
- Check data quality

### Slow Training
- Use GPU if available
- Reduce model complexity
- Optimize data loading

## Model Files

After training, you'll have:
- `checkpoint.pth` - Latest model checkpoint
- `best_model.pth` - Best model by validation loss
- `training_log.txt` - Training metrics
- `config.json` - Model configuration

## Using Your Trained Model

To use your newly trained model in WriteBot:

1. Copy the model file to the `model/` directory
2. Update the model path in the configuration
3. Restart the application

## Additional Resources

- [IAM Database Documentation](http://www.fki.inf.unibe.ch/databases/iam-on-line-handwriting-database)
- [Training Script Source](../handwriting_synthesis/training/)
- [Model Architecture Details](../docs/model_architecture.md) (if available)

## Support

For training-related issues:
- Check the error messages carefully
- Verify dataset integrity
- Ensure sufficient disk space and memory
- Consult the [main documentation](../README.md)

