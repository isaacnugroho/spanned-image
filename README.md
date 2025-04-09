# spanned-image
Compose wallpaper image for multi monitor setup by taking into account the monitor's resolution

## Requirements
* imagemagick
* xrandr

## How to Use
Just run the script:
`src/spanned-image.py source.png dest.png`

### Configuration
Say, you use dual monitors with layout aligned on top. 

```
+------------------+---------------+
|                  |               |
|   HDMI-0         |    DP-4       |
|                  |               |
|                  +---------------+
|                  |  
+------------------+
```
But, actually the second monitor is lower by 3 cm and have distant 2 cm.
```
+------------------+
|                  |  +---------------+
|   HDMI-0         |  |               |
|                  |  |    DP-4       |
|                  |  |               |
|                  |  +---------------+ 
+------------------+  
```
The custom position can be set in spanned-image.ini with the following format
```
[Config]
padding=False
crop=0
trim=False
debug=False
drawGrid=True

[HDMI-0]
offsetY=0
offsetYFrom=Zero
offsetYMode=S2S
offsetX=0
offsetXFrom=Zero
offsetXMode=F2S

[DP-4]
offsetY=30
offsetYFrom=Zero
offsetYMode=S2S
offsetX=20
offsetXFrom=HDMI-0
offsetXMode=F2S
```
Copy spanned-image.ini to ~/.config/ to be read by the script.

## TODOS

* Caching computation to speed up things
* Capability to have multiple layouts based on active monitors
* 