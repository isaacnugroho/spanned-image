#!/usr/bin/python
import screeninfo
from screeninfo import Monitor
from dataclasses import dataclass
from PIL import Image, ImageFilter
import sys
import os
import configparser


DEFAULT_DOT_PER_MM = 120 * 25.4
MAX_CROP = 34
DEBUG = False
# DEBUG = True


@dataclass
class Configuration:
  padding: bool = False
  crop: float = 0.0
  debug: bool = True
  __config = None

  def __init__(self):
    _found_config = find_config_file()
    if _found_config is not None:
      self.__config = configparser.RawConfigParser()
      self.__config.read(_found_config)
      _padding = str(self.__config.get('Config', 'padding', fallback=self.padding))
      _crop = float(self.__config.get('Config', 'crop', fallback=0.0))
      _crop = float(self.__config.get('Config', 'crop', fallback=0.0))
      self.crop = _crop if 0.0 <= _crop <= MAX_CROP else 0.0
      self.padding = _padding.upper() in ['TRUE', 'ON']

  def config(self):
    return self.__config

  def get(self, section_name, key_name, fallback=None):
    if self.__config is None:
      return fallback
    return self.__config.get(section_name, key_name, fallback=fallback)


@dataclass
class DisplayInfo:
  x: int
  y: int
  width: int
  height: int
  mm_offset_x: int = 0
  mm_offset_y: int = 0
  name: str = None
  mm_x: float = None
  mm_y: float = None
  mm_width: float = None
  mm_height: float = None
  is_primary: bool = None
  offset_x_from: str = None
  offset_y_from: str = None

  def __init__(self, monitor: Monitor, mm_offset_x: int = 0, mm_offset_y: int = 0):
    assert monitor is not None
    assert monitor.name is not None
    self.x = monitor.x
    self.y = monitor.y
    self.mm_offset_x = mm_offset_x
    self.mm_offset_y = mm_offset_y
    self.width = monitor.width
    self.height = monitor.height
    self.is_primary = (monitor.is_primary is not None and monitor.is_primary)
    self.name = monitor.name
    if monitor.width_mm is None:
      self.mm_width = monitor.width / DEFAULT_DOT_PER_MM
    else:
      self.mm_width = float(monitor.width_mm)
    if monitor.height_mm is None:
      self.mm_height = monitor.height / DEFAULT_DOT_PER_MM
    else:
      self.mm_height = float(monitor.height_mm)

  def rect(self):
    return Rect(self.x, self.y, self.width, self.height)

  def mm_rect(self):
    return Rect(self.mm_x, self.mm_y, self.mm_width, self.mm_height)

  def mm_right(self):
    return self.mm_x + self.mm_width

  def mm_bottom(self):
    return self.mm_y + self.mm_height


def build_displays(config: Configuration):
  displays = {}
  for m in screeninfo.get_monitors():
    display = DisplayInfo(m)
    displays[m.name] = display
  return normalize_displays(displays, config)


def normalize_displays(displays: {str: DisplayInfo}, config: Configuration):
  for display in displays.values():
    if config is not None:
      display.mm_offset_x = int(config.get(display.name, 'offsetX', fallback='0'))
      display.mm_offset_y = int(config.get(display.name, 'offsetY', fallback='0'))
      display.mm_offset_x_from = config.get(display.name, 'offsetXFrom', fallback=None)
      display.mm_offset_y_from = config.get(display.name, 'offsetYFrom', fallback=None)

    if display.offset_x_from is None or display.offset_x_from not in displays.keys():
      display.offset_x_from = find_display_left(display, displays)
    if display.offset_x_from is None:
      display.mm_x = display.mm_offset_x

    if display.offset_y_from is None or display.offset_y_from not in displays.keys():
      display.offset_y_from = find_display_above(display, displays)
    if display.offset_y_from is None:
      display.mm_y = display.mm_offset_y

  # set position of display with reference
  for display in displays.values():
    if display.offset_x_from is not None:
      adjust_horz_position(display, displays, [display.name])
    if display.offset_y_from is not None:
      adjust_vert_position(display, displays, [display.name])
  mm_origin_x = min([m.mm_x for m in displays.values()])
  mm_origin_y = min([m.mm_y for m in displays.values()])
  if mm_origin_y < 0 or mm_origin_x < 0:
    for display in displays.values():
      display.mm_x -= mm_origin_x
      display.mm_y -= mm_origin_y
  return displays


def find_display_left(display: DisplayInfo, displays: {str: DisplayInfo}):
  candidates = {}
  for ref in displays.values():
    if ref.name != display.name \
        and ref.x < display.x:
      delta_x = ref.x + ref.width - display.x
      delta_y = ref.y - display.y
      candidates[ref.name] = delta_x * delta_x + delta_y + delta_y
  if candidates:
    sorted_list = sorted((value, key) for (key, value) in candidates.items())
    return sorted_list[0][1]
  return None


def find_display_above(display: DisplayInfo, displays: {str: DisplayInfo}):
  candidates = {}
  for ref in displays.values():
    if ref.name != display.name \
        and ref.y < display.y:
      delta_x = ref.x - display.x
      delta_y = ref.y + ref.height - display.y
      candidates[ref.name] = delta_x * delta_x + delta_y + delta_y
  if candidates:
    sorted_list = sorted((value, key) for (key, value) in candidates.items())
    return sorted_list[0][1]
  return None


def adjust_horz_position(display: DisplayInfo, displays: {str: DisplayInfo}, visited: [str]):
  next_name = display.offset_x_from
  if next_name is None or next_name in visited:  # avoid recursive
    if display.mm_x is None:
      display.mm_x = display.mm_offset_x
  else:
    next_display = displays[next_name]
    visited += next_name
    ref_point = adjust_horz_position(next_display, displays, visited)
    display.mm_x = display.mm_offset_x + ref_point
  return display.mm_x + display.mm_width


def adjust_vert_position(display: DisplayInfo, displays: {str: DisplayInfo}, visited: [str]):
  next_name = display.offset_y_from
  if next_name is None or next_name in visited:  # avoid recursive
    if display.mm_y is None:
      display.mm_y = display.mm_offset_y
  else:
    next_display = displays[next_name]
    visited += next_name
    ref_point = adjust_vert_position(next_display, displays, visited)
    display.mm_y = display.mm_offset_y + ref_point
  return display.mm_y + display.mm_height


@dataclass
class Rect:
  x: int | float
  y: int | float
  width: int | float
  height: int | float

  def size(self):
    return int(round(self.width)), int(round(self.height))

  def position(self):
    return self.x, self.y

  def box(self):
    return int(round(self.x)), int(round(self.y)), \
           int(round(self.x + self.width)), int(round(self.y + self.height))

  def copy(self):
    return Rect(self.x, self.y, self.width, self.height)

  def __init__(self, x: int | float, y: int | float, width: int | float, height: int | float):
    self.x = x
    self.y = y
    self.width = width
    self.height = height

  def vh_ratio(self):
    return float(self.height) / self.width

  def center(self):
    return self.x + self.width / 2, self.y + self.height / 2

  def shrink(self, n=1):
    return Rect(self.x + n, self.y + n, self.width - n * 2, self.height - n * 2)

  def grow(self, n=1):
    return Rect(self.x - n, self.y - n, self.width + n * 2, self.height + n * 2)

  @staticmethod
  def of(image: Image):
    return Rect(0, 0, image.width, image.height)

  @staticmethod
  def of_tuple(values: ()):
    if values is None:
      return Rect(0, 0, 0, 0)
    if len(values) == 2:
      return Rect(0, 0, float(values[0]), float(values[1]))
    elif len(values) >= 4:
      x0 = float(values[0])
      y0 = float(values[1])
      x1 = float(values[2])
      y1 = float(values[3])
      return Rect(x0, y0, x1 - x0 + 1, y1 - y0 + 1)
    return Rect(0, 0, 0, 0)


@dataclass
class Canvas:
  displays: {str: DisplayInfo}
  __display_width: int
  __display_height: int
  __canvas_rect: Rect = None
  __canvas_ratio: float = 1.0
  __image_size: Rect = None
  __fit_rect: Rect = None
  __image: Image = None
  __padding: bool = False
  __crop: float = 0.0

  def __init__(self, displays: {str: DisplayInfo}, config: Configuration = None):
    assert displays is not None
    mm_width = max([m.mm_x + m.mm_width for m in displays.values()])
    mm_height = max([m.mm_y + m.mm_height for m in displays.values()])
    display_width = max([m.width + m.x for m in displays.values()])
    display_height = max([m.height + m.y for m in displays.values()])
    self.displays = displays
    self.__display_width = display_width
    self.__display_height = display_height
    self.__canvas_rect = Rect(0, 0, mm_width, mm_height)
    self.__canvas_ratio = self.__canvas_rect.vh_ratio()
    if config is not None:
      self.__padding = config.padding
      self.__crop = config.crop

  def display_size(self):
    return self.__display_width, self.__display_height

  def set_image(self, image: Image):
    self.__prepare_image(image)

  def get_image(self):
    return self.__image

  def paint(self) -> Image:
    target = Image.new('RGB', self.display_size(), 'black')
    if self.__image is None:
      return target

    assert self.__fit_rect is not None
    fit_rect = self.__fit_rect
    source_image = self.__image

    ratio = fit_rect.width / self.__canvas_rect.width
    if DEBUG:
      print('image_rect:', str(self.__image_size))
      print('fit_rect:', str(fit_rect))
      print('canvas_rect:', str(self.__canvas_rect))
    for display in self.displays.values():
      source_rect = Canvas.__compute_source_rect(ratio, fit_rect, display)
      if DEBUG:
        print('display:', str(display))
        print('source_rect:', str(source_rect))
      source_img = source_image.crop(source_rect.box())
      display_rect = display.rect()
      source_img = source_img.resize(display_rect.size(), Image.BILINEAR)
      target.paste(source_img, display_rect.position())

    return target

  def __prepare_image(self, image):
    image_rect = Rect.of(image)
    image_ratio = image_rect.vh_ratio()
    if self.__canvas_ratio == image_ratio:
      self.__image = image
      self.__image_size = image_rect
      self.__fit_rect = image_rect
      return
    (adjusted_image, fit_rect) = self.__adjust_image(image, image_ratio)
    self.__image = adjusted_image
    self.__image_size = Rect.of(adjusted_image)
    self.__fit_rect = fit_rect

  def __adjust_image(self, image: Image, image_ratio: float) -> (Image, Rect):
    cropped = Canvas.__crop_image(image, self.__crop, image_ratio, self.__canvas_ratio)
    image_rect = Rect.of(cropped)
    _image_ratio = image_rect.vh_ratio()
    if self.__canvas_ratio < _image_ratio:
      image_rect.height = cropped.width * self.__canvas_ratio
      image_rect.y = (cropped.height - image_rect.height) * 0.5
    else:
      image_rect.width = cropped.height / self.__canvas_ratio
      image_rect.x = (cropped.width - image_rect.width) * 0.5

    if self.__padding:
      padded = Canvas.__pad_image(cropped, image_rect, _image_ratio, self.__canvas_ratio)
      return padded, Rect.of(padded)
    return cropped, image_rect

  @staticmethod
  def __compute_source_rect(ratio: float, fit_rect: Rect, display: DisplayInfo) -> Rect:
    x = ratio * display.mm_x + fit_rect.x
    y = ratio * display.mm_y + fit_rect.y
    width = ratio * display.mm_width
    height = ratio * display.mm_height
    return Rect(x, y, width, height)

  @staticmethod
  def __pad_image(image: Image, pad_rect: Rect, image_ratio: float, canvas_ratio: float) -> Image:
    image_rect = Rect.of(image)
    from PIL import ImageFilter
    source = image.filter(ImageFilter.BoxBlur(radius=16))
    x = 0
    y = 0
    if image_ratio > canvas_ratio:
      adjusted_width = image_rect.height / canvas_ratio
      x = round((adjusted_width - image_rect.width) * 0.5)
      image_rect.width = int(round(adjusted_width))
    else:
      adjusted_height = image_rect.width * canvas_ratio
      y = round((adjusted_height - image_rect.height) * 0.5)
      image_rect.height = int(round(adjusted_height))
    target = source.resize(image_rect.size(), Image.NEAREST, pad_rect.box())
    target.paste(image, (x, y))
    return target

  @staticmethod
  def __crop_image(image: Image, crop_pct: float, image_ratio: float, canvas_ratio: float) -> Image:
    if crop_pct == 0.0 or image_ratio == canvas_ratio:
      return image
    is_wider = image_ratio < canvas_ratio
    crop = (100.0 - crop_pct) * 0.01
    feature_box = Canvas.__find_edges(image, crop, is_wider)
    target = image.crop(feature_box.box())
    if DEBUG:
      target.save('/tmp/cropped.png')
    return target

  @staticmethod
  def __find_edges(image: Image, crop: float, is_wider: bool) -> Rect:
    image_rect = Rect.of(image)
    img = image.convert('L').filter(ImageFilter.BoxBlur(radius=5))
    edge = img.filter(ImageFilter.Kernel((3, 3), (-1, -1, -1, -1, 8, -1, -1, -1, -1), 1.0, -30))
    edge = edge.crop(image_rect.shrink().box())
    box = Image.Image.getbbox(edge)
    box_rect = Rect.of_tuple(box).grow() if box is not None else image_rect.copy()
    (cx, cy) = image_rect.center()
    (bx, by) = box_rect.center()
    if DEBUG:
      print(str(image_rect), str(box_rect), bx, by, box)
      edge.save('/tmp/edge.png')

    if is_wider:
      adjusted_width = int(round(image_rect.width * crop))
      c_crop = cx * crop
      bx = max(int(round(bx - c_crop)), 0)
      if bx + adjusted_width > image_rect.width:
        bx = image_rect.width - adjusted_width - 1
      image_rect.x = bx
      image_rect.width = adjusted_width
    else:
      adjusted_height = int(round(image_rect.height * crop))
      c_crop = cy * crop
      by = max(int(round(by - c_crop)), 0)
      if by + adjusted_height > image_rect.height:
        by = image_rect.height - adjusted_height + 1
      image_rect.y = by
      image_rect.height = adjusted_height
    print(str(image_rect))
    return image_rect


# from tensorboard's util.py
def get_user_config_directory():
  if os.name == 'nt':
    appdata = os.getenv('LOCALAPPDATA')
    if appdata:
      return appdata
    appdata = os.getenv('APPDATA')
    if appdata:
      return appdata
    return None
  xdg_config_home = os.getenv('XDG_CONFIG_HOME')
  if xdg_config_home:
    return xdg_config_home
  return os.path.join(os.path.expanduser('~'), '.config')


def find_config_file():
  _local_config = os.path.join(os.path.dirname(__file__), 'spanned-image.ini')
  _user_config_path = get_user_config_directory()
  _user_config = None
  if _user_config_path is not None:
    _user_config = os.path.join(_user_config_path, 'spanned-image.ini')
  if _user_config is not None and os.path.exists(_user_config):
    return _user_config
  elif os.path.exists(_local_config):
    return _local_config
  return None


def read_image(input_file) -> Image:
  _image = Image.open(input_file, mode='r')
  return _image


def spanned_image(input_file, output_file):
  config = Configuration()
  displays = build_displays(config)
  canvas = Canvas(displays, config)
  image = read_image(input_file)
  canvas.set_image(image)
  result = canvas.paint()
  result.save(output_file)


def print_monitors():
  for m in screeninfo.get_monitors():
    print(str(m))


def print_usage():
  print('Usage: {0} <input file> <output file>'.format(sys.argv[0]))


def main():
  if len(sys.argv) != 3:
    print_usage()
    print_monitors()
    if len(sys.argv) == 2:
      image = read_image(sys.argv[1])
      print(image.size)

  else:
    spanned_image(sys.argv[1], sys.argv[2])


if __name__ == '__main__':
  main()
