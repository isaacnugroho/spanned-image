# spanned-image

Compose wallpaper image for multi monitor setup by taking into account the monitor's resolution and physical positioning

## Requirements

### System Dependencies

* Python 3.8 or higher
* xrandr (for monitor detection on Linux)

### Python Dependencies

Install via pip:

```bash
pip install -r requirements.txt
```

Or manually install:

* `screeninfo` - Monitor detection
* `pillow` - Image processing
* `tomli` - TOML parsing
* `tomli-w` - TOML writing

## Installation

Clone the repository and install dependencies:

```bash
git clone <repository-url>
cd spanned-image
pip install -r requirements.txt
```

## How to Use

Run the script with source and destination image paths:

```bash
python src/spanned_image.py source.png dest.png
```

Or make it executable and run directly:

```bash
chmod +x src/spanned_image.py
./src/spanned_image.py source.png dest.png
```

## Configuration

The script uses a TOML configuration file (`spanned-image.toml`) that supports multiple monitor profiles. The configuration file is automatically created on first run and can be placed in:

* `~/.config/spanned-image.toml` (user config directory, preferred)
* `./spanned-image.toml` (local directory, fallback)

### Profile System

The script automatically detects your monitor configuration and creates profiles based on the monitor setup. Each profile stores monitor-specific positioning data, allowing you to have different configurations for different monitor arrangements.

### Configuration Format

Say you use dual monitors with layout aligned on top:

```text
+------------------+---------------+
|                  |               |
|   HDMI-0         |    DP-4       |
|                  |               |
|                  +---------------+
|                  |  
+------------------+
```

But actually, the second monitor is lower by 3 cm and has a 2 cm gap:

```text
+------------------+
|                  |  +---------------+
|   HDMI-0         |  |               |
|                  |  |    DP-4       |
|                  |  |               |
|                  |  +---------------+ 
+------------------+  
```

The custom position can be set in `spanned-image.toml` with the following format:

```toml
[Config]
currentProfile = "profile_1"
padding = false
crop = 0.0
trim = false
debug = false
center = ""

[profile_1]
# Profile metadata (auto-generated)

[profile_1.HDMI-0]
offsetX = 0.0
offsetXFrom = "Zero"
offsetXMode = "ABS"
offsetY = 0.0
offsetYFrom = "Zero"
offsetYMode = "ABS"

[profile_1.DP-4]
offsetX = 20.0
offsetXFrom = "HDMI-0"
offsetXMode = "E2S"
offsetY = 30.0
offsetYFrom = "Zero"
offsetYMode = "ABS"
```

### Configuration Options

#### Global Options (`[Config]` section)

* `currentProfile`: The active profile name (auto-managed)
* `padding`: Add blurred padding to fill aspect ratio differences (default: `false`)
* `crop`: Percentage to crop from edges (0.0-34.0, default: `0.0`)
* `trim`: Automatically detect and trim image edges (default: `false`)
* `debug`: Enable debug logging and save debug images (default: `false`)
* `center`: Center the image on a specific monitor (monitor name or empty string)

#### Monitor Options (per monitor section)

* `offsetX`: Horizontal offset in millimeters
* `offsetXFrom`: Reference monitor for horizontal positioning (`"Zero"` for absolute positioning)
* `offsetXMode`: Reference mode for horizontal positioning (see Reference Modes below)
* `offsetY`: Vertical offset in millimeters
* `offsetYFrom`: Reference monitor for vertical positioning (`"Zero"` for absolute positioning)
* `offsetYMode`: Reference mode for vertical positioning (see Reference Modes below)

### Reference Modes

Reference modes define how a monitor's position is calculated relative to another monitor:

* `ABS` (Absolute): Position relative to origin (0,0)
* `E2S` (End to Start): Current monitor's start edge relative to reference monitor's end edge
* `S2E` (Start to End): Current monitor's end edge relative to reference monitor's start edge
* `E2E` (End to End): Current monitor's end edge relative to reference monitor's end edge

### Automatic Profile Management

The script automatically:

1. Detects your current monitor configuration
2. Creates a unique profile hash based on monitor setup
3. Creates or switches to the appropriate profile
4. Generates default monitor sections if missing

You can manually edit the configuration file to fine-tune monitor positions. The script will preserve your custom settings while automatically managing profiles.

## TODOS

* Caching computation to speed up things
* Capability to have multiple layouts based on active monitors (partially implemented via profiles)
