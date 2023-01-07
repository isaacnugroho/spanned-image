#!/usr/bin/python
import screeninfo
from screeninfo import Monitor
from dataclasses import dataclass
from PIL import Image, ImageFilter
import sys
import os
import configparser
import logging


DEFAULT_DOT_PER_MM = 120 * 25.4
MAX_CROP = 34
ZERO = 'Zero'


@dataclass
class Configuration:
  padding: bool = False
  trim: bool = False
  crop: float = 0.0
  debug: bool = False
  center: str = ''

  __config = None

  def __init__(self):
    _found_config = find_config_file()
    if _found_config is not None:
      self.__config = configparser.RawConfigParser()
      self.__config.read(_found_config)
      _crop = float(self.__config.get('Config', 'crop', fallback=0.0))
      self.crop = _crop if 0.0 <= _crop <= MAX_CROP else 0.0
      _padding = str(self.__config.get('Config', 'padding', fallback=self.padding))
      self.padding = _padding.upper() in ['TRUE', 'ON']
      _trim = str(self.__config.get('Config', 'padding', fallback=self.trim))
      self.trim = _trim.upper() in ['TRUE', 'ON']
      _debug = str(self.__config.get('Config', 'debug', fallback=self.debug))
      self.debug = _debug.upper() in ['TRUE', 'ON']

  def config(self):
    return self.__config

  def get(self, section_name, key_name, fallback=None):
    if self.__config is None:
      return fallback
    return self.__config.get(section_name, key_name, fallback=fallback)


@dataclass
class Position:
  x: int | float
  y: int | float


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
    return Position(self.x + self.width / 2, self.y + self.height / 2)

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
  __trim: bool = False
  __canvas_center: Position = None
  __offset: Position = None

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
    self.__canvas_center = self.__canvas_rect.center()
    if config is not None:
      self.__padding = config.padding
      self.__crop = config.crop
      self.__trim = config.trim
      self.__offset = self.__set_offset(config)

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
    source_image = self.__image

    ratio = self.__fit_rect.width / self.__canvas_rect.width
    logging.debug('image_rect: %s', str(self.__image_size))
    logging.debug('fit_rect: %s', str(self.__fit_rect))
    logging.debug('canvas_rect: %s', str(self.__canvas_rect))
    for display in self.displays.values():
      source_rect = Canvas.__compute_source_rect(ratio, self.__fit_rect, display)
      logging.debug('display: %s', str(display))
      logging.debug('source_rect: %s', str(source_rect))
      source_img = source_image.crop(source_rect.box())
      display_rect = display.rect()
      source_img = source_img.resize(display_rect.size(), Image.Resampling.BICUBIC)
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

  def __set_offset(self, config: Configuration):
    if config.center in self.displays.keys():
      display = self.displays[config.center]
      display_center: Position = display.mm_rect().center()
      return Position(display_center.x, display_center.y)
    return None

  def __adjust_image(self, image: Image, image_ratio: float) -> (Image, Rect):
    cropped = self.__crop_image(image, image_ratio)
    image_rect = Rect.of(cropped)
    _image_ratio = image_rect.vh_ratio()
    if self.__canvas_ratio < _image_ratio:
      image_rect.height = cropped.width * self.__canvas_ratio
      image_rect.y = (cropped.height - image_rect.height) * 0.5
    else:
      image_rect.width = cropped.height / self.__canvas_ratio
      image_rect.x = (cropped.width - image_rect.width) * 0.5

    if self.__padding:
      padded = self.__pad_image(cropped, image_rect, _image_ratio)
      return padded, Rect.of(padded)
    return cropped, image_rect

  @staticmethod
  def __compute_source_rect(ratio: float, fit_rect: Rect, display: DisplayInfo) -> Rect:
    x = ratio * display.mm_x + fit_rect.x
    y = ratio * display.mm_y + fit_rect.y
    width = ratio * display.mm_width
    height = ratio * display.mm_height
    return Rect(x, y, width, height)

  def __pad_image(self, image: Image, pad_rect: Rect, image_ratio: float) -> Image:
    image_rect = Rect.of(image)
    from PIL import ImageFilter
    source = image.filter(ImageFilter.BoxBlur(radius=16))
    x = 0
    y = 0
    if image_ratio > self.__canvas_ratio:
      adjusted_width = image_rect.height / self.__canvas_ratio
      x = round((adjusted_width - image_rect.width) * 0.5)
      image_rect.width = int(round(adjusted_width))
    else:
      adjusted_height = image_rect.width * self.__canvas_ratio
      y = round((adjusted_height - image_rect.height) * 0.5)
      image_rect.height = int(round(adjusted_height))
    target = source.resize(image_rect.size(), Image.Resampling.BILINEAR, pad_rect.box())
    target.paste(image, (x, y))
    return target

  def __crop_image(self, image: Image, image_ratio: float) -> Image:
    if self.__crop == 0.0 or image_ratio == self.__canvas_ratio:
      return image
    is_wider = image_ratio < self.__canvas_ratio
    crop = (100.0 - self.__crop) * 0.01
    feature_box = self.__find_edges(image, crop, is_wider)
    target = image.crop(feature_box.box())
    return target

  def __find_edges(self, image: Image, crop: float, is_wider: bool) -> Rect:
    image_rect = Rect.of(image)
    box_rect: Rect
    if self.__trim:
      img = image.convert('L').filter(ImageFilter.BoxBlur(radius=5))
      edge = img.filter(ImageFilter.Kernel((3, 3), (-1, -1, -1, -1, 8, -1, -1, -1, -1), 1.0, -30))
      edge = edge.crop(image_rect.shrink().box())
      box = Image.Image.getbbox(edge)
      box_rect = Rect.of_tuple(box).grow() if box is not None else image_rect.copy()
    else:
      box_rect = image_rect.copy()
    (cx, cy) = image_rect.center()
    (bx, by) = box_rect.center()
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
    return image_rect


def build_displays(config: Configuration):
  displays = {}
  for m in screeninfo.get_monitors():
    display = DisplayInfo(m)
    displays[m.name] = display
  return normalize_displays(displays, config)


def normalize_displays(displays: {str: DisplayInfo}, config: Configuration):
  setup_horizontal_positions(config, displays)
  setup_vertical_positions(config, displays)
  adjust_horizontal_positions(displays)
  adjust_vertical_positions(displays)
  normalize_positions(displays)
  return displays


def get_display_x(display: DisplayInfo):
  return display.x


def setup_horizontal_positions(config, displays):
  sorted_list = sorted(displays.values(), key=get_display_x)
  for display in sorted_list:
    if config is not None:
      display.mm_offset_x = int(config.get(display.name, 'offsetX', fallback='0'))
      display.offset_x_from = config.get(display.name, 'offsetXFrom', fallback=None)

    if display.offset_x_from == ZERO:
      display.mm_x = display.mm_offset_x
      display.offset_x_from = None
    else:
      if display.offset_x_from is None or display.offset_x_from not in displays.keys():
        display.offset_x_from = find_display_left(display, displays)
      if display.offset_x_from is None:
        display.mm_x = display.mm_offset_x
      else:
        ref_display: DisplayInfo = displays[display.offset_x_from]
        display.mm_x = ref_display.mm_x + ref_display.mm_width + display.mm_offset_x


def get_display_y(display: DisplayInfo):
  return display.y


def setup_vertical_positions(config, displays):
  sorted_list = sorted(displays.values(), key=get_display_y)
  for display in sorted_list:
    if config is not None:
      display.mm_offset_y = int(config.get(display.name, 'offsetY', fallback='0'))
      display.offset_y_from = config.get(display.name, 'offsetYFrom', fallback=None)

    if display.offset_y_from == ZERO:
      display.mm_y = display.mm_offset_x
      display.offset_y_from = None
    else:
      if display.offset_y_from is None or display.offset_y_from not in displays.keys():
        display.offset_y_from = find_display_above(display, displays)
      if display.offset_y_from is None:
        display.mm_y = display.mm_offset_y
      else:
        ref_display: DisplayInfo = displays[display.offset_y_from]
        display.mm_y = ref_display.mm_x + ref_display.mm_height + display.mm_offset_y


def adjust_horizontal_positions(displays):
  visits: {str} = []
  display_queue: [str] = []
  for display in displays.values():
    if display.offset_x_from is None:
      visits.append(display.name)
    else:
      display_queue.append(display.name)
  while len(display_queue) > 0:
    elem = display_queue.pop(0)
    display = displays[elem]
    if display.offset_x_from in visits:
      adjust_horizontal(display, displays)
      visits.append(elem)
    else:
      display_queue.append(elem)


def adjust_vertical_positions(displays):
  visits: {str} = []
  display_queue: [str] = []
  for display in displays.values():
    if display.offset_y_from is None:
      visits.append(display.name)
    else:
      display_queue.append(display.name)
  while len(display_queue) > 0:
    elem = display_queue.pop(0)
    display = displays[elem]
    if display.offset_y_from in visits:
      adjust_vertical(display, displays)
      visits.append(elem)
    else:
      display_queue.append(elem)


def normalize_positions(displays):
  mm_origin_x = min([m.mm_x for m in displays.values()])
  mm_origin_y = min([m.mm_y for m in displays.values()])
  if mm_origin_y < 0 or mm_origin_x < 0:
    for display in displays.values():
      display.mm_x -= mm_origin_x
      display.mm_y -= mm_origin_y


def find_display_left(display: DisplayInfo, displays: {str: DisplayInfo}):
  candidates = {}
  for ref in displays.values():
    if ref.name != display.name \
        and ref.x < display.x:
      delta_x = ref.x + ref.width - display.x
      delta_y = ref.y - display.y
      candidates[ref.name] = delta_x * delta_x + delta_y * delta_y
      # candidates[ref.name] = delta_x * delta_x
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
      candidates[ref.name] = delta_x * delta_x + delta_y * delta_y
      # candidates[ref.name] = delta_y * delta_y
  if candidates:
    sorted_list = sorted((value, key) for (key, value) in candidates.items())
    return sorted_list[0][1]
  return None


def adjust_horizontal(display: DisplayInfo, displays: {str: DisplayInfo}):
  next_name = display.offset_x_from
  if next_name is None:  # avoid recursive
    if display.mm_x is None:
      display.mm_x = display.mm_offset_x
  else:
    next_display = displays[next_name]
    ref_point = adjust_horizontal(next_display, displays)
    display.mm_x = display.mm_offset_x + ref_point
  return display.mm_x + display.mm_width


def adjust_vertical(display: DisplayInfo, displays: {str: DisplayInfo}):
  next_name = display.offset_y_from
  if next_name is None:  # avoid recursive
    if display.mm_y is None:
      display.mm_y = display.mm_offset_y
  else:
    next_display = displays[next_name]
    ref_point = adjust_vertical(next_display, displays)
    display.mm_y = display.mm_offset_y + ref_point
  return display.mm_y + display.mm_height


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


def spanned_image(config, input_file, output_file):
  displays = build_displays(config)
  canvas = Canvas(displays, config)
  image = read_image(input_file)
  canvas.set_image(image)
  result = canvas.paint()
  logging.debug('saving image: %s', output_file)
  try:
    result.save(output_file)
  except Exception as e:
    logging.error("saving writing %s with error %s", output_file, e)


def print_monitors():
  for m in screeninfo.get_monitors():
    print(str(m))


def print_usage():
  print('Usage: {0} <input file> <output file>'.format(sys.argv[0]))


def main():
  config = Configuration()
  if config.debug:
    logging.basicConfig(filename='/tmp/spanned_image.log', level=logging.DEBUG, format='')
  else:
    logging.basicConfig(filename='/tmp/spanned_image.log', level=logging.INFO, format='')
  logging.info('parameters: %s', sys.argv)
  if len(sys.argv) != 3:
    print_usage()
    print_monitors()
    if len(sys.argv) == 2:
      image = read_image(sys.argv[1])
      print(image.size)

  else:
    try:
      logging.debug('parameters: %s %s', sys.argv[1], sys.argv[2])
      spanned_image(config, sys.argv[1], sys.argv[2])
    except Exception as e:
      logging.error("Exception %s", e)


if __name__ == '__main__':
  main()
