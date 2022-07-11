#!/usr/bin/python

from screeninfo import Monitor, get_monitors
from dataclasses import dataclass
from PIL import Image
import sys
import os
import configparser


DEFAULT_DOT_PER_MM = 120 * 25.4


@dataclass
class MonitorInfo:
  x: int
  y: int
  width: int
  height: int
  mm_offset_x: int = 0
  mm_offset_y: int = 0
  width_mm: float = None
  height_mm: float = None
  name: str = None
  is_primary: bool = None
  mm_x: int = None
  mm_y: int = None
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
      self.width_mm = monitor.width / DEFAULT_DOT_PER_MM
    else:
      self.width_mm = float(monitor.width_mm)
    if monitor.height_mm is None:
      self.height_mm = monitor.height / DEFAULT_DOT_PER_MM
    else:
      self.height_mm = float(monitor.height_mm)


def build_monitors(config):
  monitors = {}
  for m in get_monitors():
    monitor_info = MonitorInfo(m)
    monitors[m.name] = monitor_info
    if config is not None:
      monitor_info.mm_offset_x = int(config.get(m.name, 'offsetX', fallback='0'))
      monitor_info.mm_offset_y = int(config.get(m.name, 'offsetY', fallback='0'))
      monitor_info.mm_offset_x_from = config.get(m.name, 'offsetXFrom', fallback=None)
      monitor_info.mm_offset_y_from = config.get(m.name, 'offsetYFrom', fallback=None)
  return normalize_monitors(monitors)


def normalize_monitors(monitors: {str: MonitorInfo}):
  for monitor in monitors.values():
    if monitor.offset_x_from is None or monitor.offset_x_from not in monitors.keys():
      monitor.offset_x_from = find_adjacent_monitor_horz(monitor, monitors)
    if monitor.offset_x_from is None:
      monitor.mm_x = monitor.mm_offset_x

    if monitor.offset_y_from is None or monitor.offset_y_from not in monitors.keys():
      monitor.offset_y_from = find_adjacent_monitor_vert(monitor, monitors)
    if monitor.offset_y_from is None:
      monitor.mm_y = monitor.mm_offset_y

  # set position of monitor with reference
  for monitor in monitors.values():
    if monitor.offset_x_from is not None:
      adjust_horz_position(monitor, monitors, [monitor.name])
    if monitor.offset_y_from is not None:
      adjust_vert_position(monitor, monitors, [monitor.name])
  return monitors


def find_adjacent_monitor_horz(monitor: MonitorInfo, monitors: {str: MonitorInfo}):
  candidates = {}
  for ref in monitors.values():
    if ref.name != monitor.name \
        and ref.x < monitor.x:
      delta_x = ref.x + ref.width - monitor.x
      delta_y = ref.y - monitor.y
      candidates[ref.name] = delta_x * delta_x + delta_y + delta_y

  print(str(candidates))
  if candidates:
    sorted_list = sorted((value, key) for (key, value) in candidates.items())
    return sorted_list[0][1]
  return None


def find_adjacent_monitor_vert(monitor: MonitorInfo, monitors: {str: MonitorInfo}):
  candidates = {}
  for ref in monitors.values():
    if ref.name != monitor.name \
        and ref.y < monitor.y:
      delta_x = ref.x - monitor.x
      delta_y = ref.y + ref.height - monitor.y
      candidates[ref.name] = delta_x * delta_x + delta_y + delta_y

  print(str(candidates))
  if candidates:
    sorted_list = sorted((value, key) for (key, value) in candidates.items())
    return sorted_list[0][1]
  return None


def adjust_horz_position(monitor: MonitorInfo, monitors: {str: MonitorInfo}, visited: [str]):
  next_name = monitor.offset_x_from
  if next_name is None or next_name in visited:  # avoid recursive
    if monitor.mm_x is None:
      monitor.mm_x = monitor.mm_offset_x
  else:
    next_monitor = monitors[next_name]
    visited += next_name
    ref_point = adjust_horz_position(next_monitor, monitors, visited)
    monitor.mm_x = monitor.mm_offset_x + ref_point
  return monitor.mm_x + monitor.width_mm


def adjust_vert_position(monitor: MonitorInfo, monitors: {str: MonitorInfo}, visited: [str]):
  next_name = monitor.offset_y_from
  if next_name is None or next_name in visited:  # avoid recursive
    if monitor.mm_y is None:
      monitor.mm_y = monitor.mm_offset_y
  else:
    next_monitor = monitors[next_name]
    visited += next_name
    ref_point = adjust_vert_position(next_monitor, monitors, visited)
    monitor.mm_y = monitor.mm_offset_y + ref_point
  return monitor.mm_y + monitor.height_mm


@dataclass
class Rect:
  x: float
  y: float
  width: float
  height: float


@dataclass
class Canvas:
  monitors: {str: MonitorInfo}
  display_width: int
  display_height: int
  canvas_rect: Rect
  image_rect: Rect = None
  _image: Image = None

  def __init__(self, monitors):
    mm_origin_x = min([m.mm_x for m in monitors.values()])
    mm_origin_y = min([m.mm_y for m in monitors.values()])
    mm_width = max([m.mm_x + m.width_mm for m in monitors.values()]) - mm_origin_x
    mm_height = max([m.mm_y + m.height_mm for m in monitors.values()]) - mm_origin_y
    display_width = max([m.width + m.x for m in monitors.values()])
    display_height = max([m.height + m.y for m in monitors.values()])
    self.monitors = monitors
    self.display_width = display_width
    self.display_height = display_height
    self.canvas_rect = Rect(mm_origin_x, mm_origin_y, mm_width, mm_height)

  def set_image(self, image: Image):
    self._image = image
    canvas_ratio = float(self.canvas_rect.height) / self.canvas_rect.width
    image_ratio = float(image.height) / image.width
    x = 0.0
    y = 0.0
    width = float(image.width)
    height = float(image.height)
    if canvas_ratio <= image_ratio:
      height = image.width * canvas_ratio
      y = (image.height - height) * 0.5
    else:
      width = image.height / canvas_ratio
      x = (image.width - width) * 0.5
    self.image_rect = Rect(x, y, width, height)

  def get_image(self):
    return self._image

  def paint(self) -> Image:
    result = Image.new('RGB', (self.display_width, self.display_height), 'black')
    if self._image is None:
      return result

    assert self.image_rect is not None
    horz_ratio = self.image_rect.width / self.canvas_rect.width
    vert_ratio = self.image_rect.height / self.canvas_rect.height

    for m in self.monitors.values():
      x1 = horz_ratio * (m.mm_x - self.canvas_rect.x) + self.image_rect.x
      y1 = vert_ratio * (m.mm_y - self.canvas_rect.y) + self.image_rect.y
      x2 = horz_ratio * m.width_mm + x1 - 1.0
      y2 = vert_ratio * m.height_mm + y1 - 1.0
      src_box = (int(x1), int(y1), int(x2), int(y2))
      source_img = self._image.crop(src_box)
      print(str(src_box), y2 / x2)
      print(str(source_img.size), float(source_img.height) / source_img.width)
      from PIL.Image import BICUBIC
      source_img = source_img.resize((m.width, m.height), BICUBIC)
      target_box = (m.x, m.y)
      result.paste(source_img, target_box)
      print(str(target_box))
      print(str(source_img.size), float(source_img.height) / source_img.width)
    return result


# from tensorboard's util.py
def get_user_config_directory():
  if os.name == 'nt':
    appdata = os.getenv('LOCALAPPDATA')
    if appdata:
      return appdata
    appdata = os.getenv('APPDATA')
    if appdata:
      return appdata
    appdata = os.getenv('PUBLIC')
    if appdata:
      return appdata
    return None
  xdg_config_home = os.getenv('XDG_CONFIG_HOME')
  if xdg_config_home:
    return xdg_config_home
  return os.path.join(os.path.expanduser('~'), '.config')


def find_config_file():
  _config_location = os.path.join(os.path.dirname(__file__), 'spanned-image.ini')
  if os.path.exists(_config_location):
    return _config_location
  _user_config_path = get_user_config_directory()
  if _user_config_path is None:
    return None
  _config_location = os.path.join(_user_config_path, 'spanned-image.ini')
  if os.path.exists(_config_location):
    return _config_location
  return None


def read_config_file():
  _config_file = find_config_file()
  if _config_file is None:
    return None
  config = configparser.RawConfigParser()
  config.read(_config_file)
  return config


def read_image(input_file) -> Image:
  _image = Image.open(input_file, mode='r')
  return _image


def spanned_image(input_file, output_file):
  config = read_config_file()
  monitors = build_monitors(config)
  canvas = Canvas(monitors)
  image = read_image(input_file)
  canvas.set_image(image)
  print(str(canvas))
  result = canvas.paint()
  result.save(output_file)


def print_monitors():
  for m in get_monitors():
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
