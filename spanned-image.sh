#!/bin/bash

declare -a MONITORS
declare -a CUSTOM_MONITORS

declare -a REF_MON_H
declare -a REF_MON_V

declare -r pxWidth=1
declare -r pxHeight=2
declare -r mmWidth=3
declare -r mmHeight=4
declare -r pixelX=5
declare -r pixelY=6
declare -r mmOffsetX=7
declare -r mmOffsetY=8
declare -r cropX=9
declare -r cropY=10
declare -r cropW=11
declare -r cropH=12

declare -i NUM_MONITORS
declare -i CANVAS_WIDTH=0
declare -i CANVAS_HEIGHT=0
declare -i TARGET_WIDTH_MM=0
declare -i TARGET_HEIGHT_MM=0
declare -i IMAGE_WIDTH=256
declare -i IMAGE_HEIGHT=256
declare -i USABLE_WIDTH=256
declare -i USABLE_HEIGHT=256
declare -i USABLE_OFFSET_X=0
declare -i USABLE_OFFSET_Y=0

declare -a tmpMon

CUSTOM_CONFIGURATION=~/.config/spanned-image.conf

get_image_size() {
  if [[ ! -z "$1" && -e "$1" ]]; then
    eval $(identify -format 'export IMAGE_WIDTH=%w IMAGE_HEIGHT=%h' "$1")
  else
    IMAGE_WIDTH=0
    IMAGE_HEIGHT=0
  fi
}

determine_canvas() {
  (( i = 0 ))
  while [[ $i -lt $NUM_MONITORS ]]; do
    tmpMon=(${MONITORS[$i]})
    (( _tWidth = tmpMon[${pxWidth}] + tmpMon[${pixelX}] ))
    if [[ ${CANVAS_WIDTH} -lt ${_tWidth} ]]; then
      (( CANVAS_WIDTH = _tWidth ))
    fi

    (( _tHeight = tmpMon[${pxHeight}] + tmpMon[${pixelY}] ))
    if [[ ${CANVAS_HEIGHT} -lt ${_tHeight} ]]; then
      (( CANVAS_HEIGHT = _tHeight ))
    fi
    (( i = i + 1 ))
  done
}

determine_references() {
  (( i = 0 ))
  while [[ $i -lt $NUM_MONITORS ]]; do
    tmpMon=(${MONITORS[$i]})

    if [[ ${tmpMon[${pixelX}]} -eq 0 ]]; then
      if [[ -z "${REF_MON_H[0]}" || ${REF_MON_H[$pxWidth]} -lt ${tmpMon[$pxWidth]} ]]; then
        REF_MON_H=(${tmpMon[*]})
      fi
    fi
    if [[ ${tmpMon[${pixelY}]} -eq 0 ]]; then
      if [[ -z "${REF_MON_H[0]}" || ${REF_MON_V[$pxHeight]} -lt ${tmpMon[$pxHeight]} ]]; then
        REF_MON_V=(${tmpMon[*]})
      fi
    fi

    (( i = i + 1 ))
  done
}

determine_offsets() {
  determine_references

  declare -a tmpArr
  declare -i adjustX
  declare -i adjustY

  (( i = 0 ))
  (( adjustX = 0 ))
  (( adjustY = 0 ))

  while [[ $i -lt $NUM_MONITORS ]]; do
    tmpMon=(${MONITORS[$i]})

    if [[ ${tmpMon[${pixelX}]} -eq 0 ]]; then
      (( tmpMon[${mmOffsetX}] = 0 ))
    else
      (( tmpMon[${mmOffsetX}] = REF_MON_H[${mmWidth}] + ((tmpMon[${pixelX}] - REF_MON_H[${pxWidth}]) * tmpMon[${mmWidth}] + tmpMon[${pxWidth}] / 2) / tmpMon[${pxWidth}] ))
    fi

    if [[ ${tmpMon[${pixelY}]} -eq 0 ]]; then
      (( tmpMon[${mmOffsetY}] = 0 ))
    else
      (( tmpMon[${mmOffsetY}] = REF_MON_V[${mmHeight}] + ((tmpMon[${pixelY}] - REF_MON_V[${pxHeight}]) * tmpMon[${mmHeight}] + tmpMon[${pxHeight}] / 2) / tmpMon[${pxHeight}] ))
    fi

    (( j = 0 ))
    while [[ $j -lt ${#CUSTOM_MONITORS[*]} ]]; do 
      tmpArr=(${CUSTOM_MONITORS[j]})
      if [[ "${tmpArr[0]}" == "${tmpMon[0]}" ]]; then
        if [[ "${tmpArr[1]}" -ne 0 ]]; then
          (( tmpMon[${mmOffsetX}] = tmpMon[${mmOffsetX}] + tmpArr[1] ))
          if [[ $adjustX -gt tmpMon[${mmOffsetX}] ]]; then
            (( adjustX = tmpMon[${mmOffsetX}] ))
          fi
        fi
        if [[ "${tmpArr[2]}" -ne 0 ]]; then
          (( tmpMon[${mmOffsetY}] = tmpMon[${mmOffsetY}] + tmpArr[2] ))
          if [[ $adjustY -gt tmpMon[${mmOffsetY}] ]]; then
            (( adjustY = tmpMon[${mmOffsetY}] ))
          fi
        fi
      fi
      (( j = j + 1 ))
    done

    MONITORS[$i]="${tmpMon[*]}"
    (( i = i + 1 ))
  done

  if [[ $adjustX -lt 0 || $adjustY -lt 0 ]]; then
    (( i = 0 ))
    while [[ $i -lt $NUM_MONITORS ]]; do
      tmpMon=(${MONITORS[$i]})
      (( tmpMon[${mmOffsetX}] = tmpMon[${mmOffsetX}] - adjustX ))
      (( tmpMon[${mmOffsetY}] = tmpMon[${mmOffsetY}] - adjustY ))
      MONITORS[$i]="${tmpMon[*]}"
      (( i = i + 1 ))
    done
  fi
}

determine_area() {
  determine_offsets

  (( i = 0 ))
  while [[ $i -lt $NUM_MONITORS ]]; do
    tmpMon=(${MONITORS[$i]})
    (( _tWidth = tmpMon[${mmWidth}] + tmpMon[${mmOffsetX}] ))
    if [[ ${TARGET_WIDTH_MM} -lt ${_tWidth} ]]; then
      (( TARGET_WIDTH_MM = ${_tWidth} ))
    fi

    (( _tHeight = tmpMon[${mmHeight}] + tmpMon[${mmOffsetY}] ))
    if [[ ${TARGET_HEIGHT_MM} -lt ${_tHeight} ]]; then
      (( TARGET_HEIGHT_MM = ${_tHeight} ))
    fi
    (( i = i + 1 ))
  done
}

calculate_image() {
  (( _t1 = (IMAGE_WIDTH * TARGET_HEIGHT_MM + TARGET_WIDTH_MM / 2) / TARGET_WIDTH_MM ))
  (( _t2 = (IMAGE_HEIGHT * TARGET_WIDTH_MM + TARGET_HEIGHT_MM / 2) / TARGET_HEIGHT_MM ))
  if [[ $_t1 -le $IMAGE_HEIGHT ]]; then
    (( USABLE_WIDTH = IMAGE_WIDTH ))
    (( USABLE_HEIGHT = _t1 ))
    (( USABLE_OFFSET_X = 0 ))
    (( USABLE_OFFSET_Y = 2 * (IMAGE_HEIGHT - USABLE_HEIGHT) / 5 ))
  else
    (( USABLE_WIDTH = _t2 ))
    (( USABLE_HEIGHT = IMAGE_HEIGHT ))
    (( USABLE_OFFSET_X = (IMAGE_WIDTH - USABLE_WIDTH) / 2 ))
    (( USABLE_OFFSET_Y = 0 ))
  fi
}

calculate_cropping() {
  (( i = 0 ))
  while [[ $i -lt $NUM_MONITORS ]]; do
    tmpMon=(${MONITORS[$i]})

    (( tmpMon[${cropX}] = USABLE_OFFSET_X + (tmpMon[${mmOffsetX}] * USABLE_WIDTH + TARGET_WIDTH_MM / 2) / TARGET_WIDTH_MM )) 
    (( tmpMon[${cropY}] = USABLE_OFFSET_Y + (tmpMon[${mmOffsetY}] * USABLE_HEIGHT + TARGET_HEIGHT_MM / 2) / TARGET_HEIGHT_MM )) 
    (( tmpMon[${cropW}] = (tmpMon[${mmWidth}] * USABLE_WIDTH + TARGET_WIDTH_MM / 2) / TARGET_WIDTH_MM )) 
    (( tmpMon[${cropH}] = (tmpMon[${mmHeight}] * USABLE_HEIGHT + TARGET_HEIGHT_MM / 2) / TARGET_HEIGHT_MM )) 

    MONITORS[$i]="${tmpMon[*]}"
    (( i = i + 1 ))
  done
}

# use imagemagick for composing image
create_image() {
  CMD="convert \""$1"\" "
  (( i = 0 ))
  while [[ $i -lt $NUM_MONITORS ]]; do
    tmpMon=(${MONITORS[$i]})
    CMD+="\\( -clone 0 -crop ${tmpMon[${cropW}]}x${tmpMon[${cropH}]}+${tmpMon[${cropX}]}+${tmpMon[${cropY}]} -resize ${tmpMon[${pxWidth}]}x${tmpMon[${pxHeight}]}! -set page +${tmpMon[${pixelX}]}+${tmpMon[${pixelY}]} \\) "
    (( i = i + 1 ))
  done
  CMD+="-delete 0 -set page ${CANVAS_WIDTH}x${CANVAS_HEIGHT} -flatten \""$2"\""

  eval $CMD
}

print_variables() {
  echo "NUM_MONITORS=$NUM_MONITORS"
  echo "CANVAS_WIDTH=$CANVAS_WIDTH"
  echo "CANVAS_HEIGHT=$CANVAS_HEIGHT"
  echo "TARGET_WIDTH_MM=$TARGET_WIDTH_MM"
  echo "TARGET_HEIGHT_MM=$TARGET_HEIGHT_MM"
  echo "IMAGE_WIDTH=$IMAGE_WIDTH"
  echo "IMAGE_HEIGHT=$IMAGE_HEIGHT" 
  echo "USABLE_WIDTH=$USABLE_WIDTH"
  echo "USABLE_HEIGHT=$USABLE_HEIGHT"
  echo "USABLE_OFFSET_X=$USABLE_OFFSET_X"
  echo "USABLE_OFFSET_Y=$USABLE_OFFSET_Y"
  echo "MONITORS=(${MONITORS[@]})"
  echo "REF_MON_H=(${REF_MON_H[@]})"
  echo "REF_MON_V=(${REF_MON_V[@]})"
  echo "CUSTOM_MONITORS=(${CUSTOM_MONITORS[@]})"

  echo "pxWidth=${pxWidth}"
  echo "pxHeight=${pxHeight}"
  echo "mmWidth=${mmWidth}"
  echo "mmHeight=${mmHeight}"
  echo "pixelX=${pixelX}"
  echo "pixelY=${pixelY}"
  echo "mmOffsetX=${mmOffsetX}"
  echo "mmOffsetY=${mmOffsetY}"
  echo "cropX=${cropX}"
  echo "cropY=${cropY}"
  echo "cropW=${cropW}"
  echo "cropH=${cropH}"
}

main_routine() {
  if [[ -e "$CUSTOM_CONFIGURATION" ]]; then
    source "$CUSTOM_CONFIGURATION"
  fi
  eval $(xrandr --listactivemonitors \
    | sed -r -e 's#([0-9]+)/([0-9]+)x([0-9]+)/([0-9]+)\+([0-9]+)\+([0-9]+)#\1 \2 \3 \4 \5 \6 #g' -e 's/^ *([0-9]+):\s+/\1 /' -e 's/[: ]+/ /g' \
    | awk -F '[ :]' '/^Monitors/ { print "NUM_MONITORS=" $2 } \
        /^[0-9]+/ { printf "MON_%s=(%s %s %s %s %s %s %s)\nMONITORS+=(\"%s %s %s %s %s %s %s\")\n", $1, $9, $3, $5, $4, $6, $7, $8, $9, $3, $5, $4, $6, $7, $8 }' )

  if [[ "$NUM_MONITORS" -eq 1 ]]; then
    cp $1 $2
  else
    get_image_size "$1"

    if [[ "$IMAGE_WIDTH" -gt 0 ]]; then
      determine_canvas
      determine_area
      calculate_image
      calculate_cropping
      create_image "$1" "$2"
    fi
  fi
}

main_routine "$1" "$2"
# print_variables
