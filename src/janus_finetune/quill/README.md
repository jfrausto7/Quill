# Janus Form-Filling Assistant

This project implements a fine-tuning pipeline for the Janus multimodal model, specifically designed for form-filling assistance. The model is trained to understand form layouts and help users complete forms through natural conversation.

## Current Status and Known Issues

⚠️ **Work in Progress**: This notebook is currently in development and will be updated in our next sprint.

### Known Bugs:
- There's a conversation format issue causing a TypeError (`list indices must be integers or slices, not str`). This is related to how the model processes conversation structures and will be fixed in the next update.
- The current implementation requires specific conversation formatting that needs to be optimized.

## Setup Requirements

### Environment Setup
```bash
!git clone https://github.com/deepseek-ai/Janus.git
%cd Janus
!pip install -e .
!pip install flash-attn
```

### Image Requirements
- Place your form image(s) in the `/content/Janus/images/` directory
- Default form image path: `/content/Janus/images/demoForm1.png`
- Supported image formats: PNG, JPG

## Features

### Current Implementation
- Multimodal training pipeline for form understanding
- Custom conversation formatting for form-filling tasks
- Support for multiple training examples
- Configurable training parameters
- Device-aware processing (CPU, CUDA, MPS)

### Configuration Options
```python
config = {
    "model_path": "deepseek-ai/Janus-1.3B",
    "form_image_path": "/path/to/form.png",
    "output_dir": "./janus_finetuned",
    "batch_size": 4,
    "num_epochs": 3,
    "learning_rate": 5e-5,
    "logging_dir": "./logs"
}
```

## Usage

### Basic Usage
```python
trainer = JanusFormTrainer(
    model_path="deepseek-ai/Janus-1.3B",
    form_image_path="/content/Janus/images/demoForm1.png"
)
trainer.train()
```

### Custom Training Data
You can modify the `prepare_training_data` method to include your own training examples:
```python
def prepare_training_data(self):
    return [
        {
            "conversation": [
                {"role": "user", "content": "Your custom question"},
                {"role": "assistant", "content": "Your custom response"}
            ],
            "image_path": self.config["form_image_path"]
        }
    ]
```

## Upcoming Updates

In the next sprint, we plan to:
- Fix the conversation format bug
- Improve error handling
- Add more training examples
- Optimize image processing
- Add validation dataset support
- Complete the next task: Filling

## License

This project uses the Janus model from Deepseek AI and follows their licensing requirements.

---

**Note**: This implementation is part of our ongoing development sprint. Please check back for updates and improvements.
