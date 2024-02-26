import unittest
from unittest import TestCase

from screeninfo import Monitor

from spanned_image import DisplayInfo, normalize_displays, find_display_left


class Test(TestCase):
  @staticmethod
  def test_find_adjacent_monitor_h():
    monitors = {
        'a': DisplayInfo(
            Monitor(name='a', x=0, y=0, width=800, height=600, width_mm=8000, height_mm=6000)),
        'b': DisplayInfo(
            Monitor(name='b', x=1024, y=0, width=1024, height=768, width_mm=10240, height_mm=7680),
            mm_offset_x=5),
        'c': DisplayInfo(
            Monitor(name='c', x=0, y=600, width=1024, height=768, width_mm=10240, height_mm=7680),
            mm_offset_x=5),
    }
    monitor_b = monitors['b']
    left_of_b = find_display_left(monitor_b, monitors)
    print(left_of_b)
    assert left_of_b == 'c'

    monitor_c = monitors['c']
    left_of_c = find_display_left(monitor_c, monitors)
    print(left_of_c)
    assert left_of_c is None

  @staticmethod
  def test_normalize_monitors():
    monitors = {
        'a': DisplayInfo(
            Monitor(name='a', x=0, y=0, width=800, height=600, width_mm=8000, height_mm=6000)),
        'b': DisplayInfo(
            Monitor(name='b', x=800, y=0, width=1024, height=768, width_mm=10240, height_mm=7680),
            mm_offset_x=5),
        'c': DisplayInfo(
            Monitor(name='c', x=1824, y=0, width=1024, height=768, width_mm=10240, height_mm=7680),
            mm_offset_x=10),
    }
    normalize_displays(monitors)
    assert monitors['b'].mm_x == 8005
    assert monitors['c'].mm_x == 18255
    print(str(monitors))


if __name__ == '__main__':
  unittest.main()
