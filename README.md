# spanned-image
Compose wallpaper image for multi monitor setup by taking into account the monitor's resolution

## Requirements
* imagemagick
* xrandr

## How to Use
Just run the script:
`./spanned-image.sh source.png dest.png`

### Customization
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
The custom position can be set in spanned-image.conf with the following format
```
CUSTOM_MONITORS=( "<monitor name> <x offset> <y offset>" )
```
`x offset`: horizontal offset in mm
`y offset`: vertical offset in mm below its virtual position

And the setup for the above case is:
`CUSTOM_MONITORS=( "DP-4 20 30" )`

Copy spanned-image.conf to ~/.config/ to be read by the script.

Enjoy!