import unittest
from unittest import TestCase
from unittest.mock import Mock, patch
import tempfile
import os
import hashlib

from screeninfo import Monitor

from src.spanned_image import (
    DisplayInfo, normalize_displays, find_display_left,
    Configuration, determine_profile, populate_profile,
    ReferenceMode
)


class Test(TestCase):
  @staticmethod
  def test_find_adjacent_monitor_h():
    monitors = {
        'a': DisplayInfo(
            Monitor(name='a', x=0, y=0, width=800, height=600, width_mm=8000, height_mm=6000)),
        'b': DisplayInfo(
            Monitor(name='b', x=1024, y=0, width=1024, height=768, width_mm=10240, height_mm=7680)),
        'c': DisplayInfo(
            Monitor(name='c', x=0, y=600, width=1024, height=768, width_mm=10240, height_mm=7680)),
    }
    monitor_b = monitors['b']
    left_of_b = find_display_left(monitor_b, list(monitors.values()))
    print(left_of_b)
    assert left_of_b.name == 'a'

    monitor_c = monitors['c']
    left_of_c = find_display_left(monitor_c, list(monitors.values()))
    print(left_of_c)
    assert left_of_c is None

  @staticmethod
  def test_normalize_monitors():
    monitors = {
        'a': DisplayInfo(
            Monitor(name='a', x=0, y=0, width=800, height=600, width_mm=8000, height_mm=6000)),
        'b': DisplayInfo(
            Monitor(name='b', x=800, y=0, width=1024, height=768, width_mm=10240, height_mm=7680)),
        'c': DisplayInfo(
            Monitor(name='c', x=1824, y=0, width=1024, height=768, width_mm=10240, height_mm=7680)),
    }
    normalize_displays(monitors)
    assert monitors['b'].mm_x == 8000
    assert monitors['c'].mm_x == 18240
    print(str(monitors))


class TestConfiguration(TestCase):
  """Tests for Configuration class methods."""

  def setUp(self):
    """Set up test fixtures."""
    self.temp_dir = tempfile.mkdtemp()
    self.temp_config_file = os.path.join(self.temp_dir, 'spanned-image.toml')

  def tearDown(self):
    """Clean up test fixtures."""
    if os.path.exists(self.temp_config_file):
      os.remove(self.temp_config_file)
    os.rmdir(self.temp_dir)

  @patch('src.spanned_image.find_config_file')
  def test_create_profile(self, mock_find_config):
    """Test creating a new profile."""
    mock_find_config.return_value = None
    mock_monitor = Mock(spec=Monitor)
    mock_monitor.name = 'DP-1'
    config = Configuration([mock_monitor])
    config._Configuration__config_file = self.temp_config_file
    config._Configuration__config = {}
    
    monitor_data = "Monitor(name='DP-1', x=0, y=0, width=1920, height=1080)"
    monitor_names = ['DP-1']
    hash_value = hashlib.md5(monitor_data.encode('utf-8')).hexdigest()
    
    config.create_profile('profile_test', monitor_data, monitor_names, hash_value)
    
    self.assertIn('profile_test', config._Configuration__config)
    profile = config._Configuration__config['profile_test']
    self.assertEqual(profile['monitorData'], monitor_data)
    self.assertEqual(profile['monitors'], monitor_names)
    self.assertEqual(profile['hashValue'], hash_value)

  @patch('src.spanned_image.find_config_file')
  def test_find_profile_by_hash(self, mock_find_config):
    """Test finding a profile by hash value."""
    mock_find_config.return_value = None
    mock_monitor = Mock(spec=Monitor)
    mock_monitor.name = 'DP-1'
    config = Configuration([mock_monitor])
    config._Configuration__config = {}
    
    hash_value = 'abcdef1234567890'
    config.create_profile('profile_test', 'data', ['DP-1'], hash_value)
    
    found = config.find_profile_by_hash(hash_value)
    self.assertEqual(found, 'profile_test')
    
    not_found = config.find_profile_by_hash('nonexistent')
    self.assertIsNone(not_found)

  @patch('src.spanned_image.find_config_file')
  def test_has_monitor_section(self, mock_find_config):
    """Test checking if a monitor section exists."""
    mock_find_config.return_value = None
    mock_monitor = Mock(spec=Monitor)
    mock_monitor.name = 'DP-1'
    config = Configuration([mock_monitor])
    config._Configuration__config = {}
    config._Configuration__current_profile = 'profile_test'
    config._Configuration__config['profile_test'] = {
      'DP-1': {'offsetX': 0.0, 'offsetY': 0.0}
    }
    
    self.assertTrue(config.has_monitor_section('DP-1'))
    self.assertFalse(config.has_monitor_section('DP-2'))

  @patch('src.spanned_image.find_config_file')
  def test_add_monitor_section(self, mock_find_config):
    """Test adding a monitor section to a profile."""
    mock_find_config.return_value = None
    mock_monitor = Mock(spec=Monitor)
    mock_monitor.name = 'DP-1'
    config = Configuration([mock_monitor])
    config._Configuration__config = {}
    config._Configuration__current_profile = 'profile_test'
    config._Configuration__config_file = self.temp_config_file
    config._Configuration__config['profile_test'] = {}
    
    config.set_monitor_section('DP-1', 'Zero', ReferenceMode.Absolute, 10.5, 'Zero', ReferenceMode.Absolute, 20.3)
    
    profile = config._Configuration__config['profile_test']
    self.assertIn('DP-1', profile)
    self.assertEqual(profile['DP-1']['offsetX'], 10.5)
    self.assertEqual(profile['DP-1']['offsetY'], 20.3)

  @patch('src.spanned_image.find_config_file')
  def test_set_current_profile(self, mock_find_config):
    """Test setting the current profile."""
    mock_find_config.return_value = None
    mock_monitor = Mock(spec=Monitor)
    mock_monitor.name = 'DP-1'
    config = Configuration([mock_monitor])
    config._Configuration__config = {}
    config._Configuration__config_file = self.temp_config_file
    config._Configuration__config['Config'] = {}
    
    config.set_current_profile('profile_new')
    
    self.assertEqual(config._Configuration__current_profile, 'profile_new')
    self.assertEqual(config._Configuration__config['Config']['currentProfile'], 'profile_new')

  @patch('src.spanned_image.find_config_file')
  def test_currentProfile_returns_display_config(self, mock_find_config):
    """Test getting DisplayConfig for a monitor."""
    mock_find_config.return_value = None
    mock_monitor = Mock(spec=Monitor)
    mock_monitor.name = 'DP-1'
    config = Configuration([mock_monitor])
    config._Configuration__config = {}
    config._Configuration__current_profile = 'profile_test'
    config._Configuration__config['profile_test'] = {
      'DP-1': {
        'offsetX': 100.0,
        'offsetY': 50.0,
        'offsetXFrom': 'Zero',
        'offsetYFrom': 'Zero'
      }
    }
    
    display_config = config.currentProfile('DP-1')
    self.assertEqual(display_config.offsetX, 100.0)
    self.assertEqual(display_config.offsetY, 50.0)


class TestDetermineProfile(TestCase):
  """Tests for determine_profile function."""

  @patch('src.spanned_image.screeninfo.get_monitors')
  @patch('src.spanned_image.find_config_file')
  def test_determine_profile_creates_new_profile(self, mock_find_config, mock_get_monitors):
    """Test that determine_profile creates a new profile when none exists."""
    mock_find_config.return_value = None
    mock_monitor = Mock(spec=Monitor)
    mock_monitor.name = 'DP-1'
    mock_monitor.x = 0
    mock_monitor.y = 0
    mock_monitor.width = 1920
    mock_monitor.height = 1080
    mock_get_monitors.return_value = [mock_monitor]
    
    config = Configuration([mock_monitor])
    config._Configuration__config = {}
    config._Configuration__config_file = tempfile.mktemp()
    
    determine_profile(config)
    
    # Check that a profile was created
    profile_keys = [k for k in config._Configuration__config.keys() if k.startswith('profile_')]
    self.assertEqual(len(profile_keys), 1)
    
    profile_name = profile_keys[0]
    profile = config._Configuration__config[profile_name]
    self.assertIn('monitorData', profile)
    self.assertIn('monitors', profile)
    self.assertIn('hashValue', profile)
    self.assertEqual(config._Configuration__current_profile, profile_name)

  @patch('src.spanned_image.screeninfo.get_monitors')
  @patch('src.spanned_image.find_config_file')
  def test_determine_profile_finds_existing_profile(self, mock_find_config, mock_get_monitors):
    """Test that determine_profile finds and uses an existing profile."""
    mock_find_config.return_value = None
    mock_monitor = Mock(spec=Monitor)
    mock_monitor.name = 'DP-1'
    mock_monitor.x = 0
    mock_monitor.y = 0
    mock_monitor.width = 1920
    mock_monitor.height = 1080
    mock_get_monitors.return_value = [mock_monitor]
    
    config = Configuration([mock_monitor])
    config._Configuration__config = {}
    config._Configuration__config_file = tempfile.mktemp()
    
    # Create a profile manually first
    monitor_data_str = ';'.join(str(m) for m in [mock_monitor])
    hash_value = hashlib.md5(monitor_data_str.encode('utf-8')).hexdigest()
    profile_name = 'profile_existing'
    config.create_profile(profile_name, monitor_data_str, ['DP-1'], hash_value)
    
    # Now determine profile should find it
    determine_profile(config)
    
    self.assertEqual(config._Configuration__current_profile, profile_name)


class TestPopulateProfile(TestCase):
  """Tests for populate_profile function."""

  @patch('src.spanned_image.screeninfo.get_monitors')
  @patch('src.spanned_image.find_config_file')
  @patch.object(Configuration, '_write_config')
  def test_populate_profile_creates_missing_sections(self, mock_write_config, mock_find_config, mock_get_monitors):
    """Test that populate_profile creates missing monitor sections."""
    mock_find_config.return_value = None
    mock_monitor1 = Mock(spec=Monitor)
    mock_monitor1.name = 'DP-1'
    mock_monitor1.x = 0
    mock_monitor1.y = 0
    mock_monitor1.width = 1920
    mock_monitor1.height = 1080
    mock_monitor1.width_mm = None
    mock_monitor1.height_mm = None
    mock_monitor1.is_primary = False
    
    mock_monitor2 = Mock(spec=Monitor)
    mock_monitor2.name = 'DP-2'
    mock_monitor2.x = 1920
    mock_monitor2.y = 0
    mock_monitor2.width = 1920
    mock_monitor2.height = 1080
    mock_monitor2.width_mm = None
    mock_monitor2.height_mm = None
    mock_monitor2.is_primary = False
    
    mock_get_monitors.return_value = [mock_monitor1, mock_monitor2]
    
    config = Configuration([mock_monitor1, mock_monitor2])
    config._Configuration__config = {}
    config._Configuration__current_profile = 'profile_test'
    config._Configuration__config_file = tempfile.mktemp()
    config._Configuration__config['profile_test'] = {}
    
    populate_profile(config)
    
    profile = config._Configuration__config['profile_test']
    self.assertIn('DP-1', profile)
    self.assertIn('DP-2', profile)
    
    # Check that DP-1 is positioned absolutely at 0
    self.assertEqual(profile['DP-1']['offsetX'], 0.0)
    self.assertEqual(profile['DP-1']['offsetXFrom'], 'Zero')
    self.assertEqual(profile['DP-1']['offsetXMode'], 'ABS')
    
    # Check that DP-2 is positioned relative to DP-1 (EndToStart mode)
    # DP-2 starts right after DP-1 ends, so offset is 0.0
    self.assertEqual(profile['DP-2']['offsetX'], 0.0)
    self.assertEqual(profile['DP-2']['offsetXFrom'], 'DP-1')
    self.assertEqual(profile['DP-2']['offsetXMode'], 'E2S')
    
    # Verify that _write_config was called
    self.assertGreater(mock_write_config.call_count, 0)

  @patch('src.spanned_image.screeninfo.get_monitors')
  @patch('src.spanned_image.find_config_file')
  def test_populate_profile_skips_existing_sections(self, mock_find_config, mock_get_monitors):
    """Test that populate_profile doesn't overwrite existing monitor sections."""
    mock_find_config.return_value = None
    mock_monitor = Mock(spec=Monitor)
    mock_monitor.name = 'DP-1'
    mock_monitor.x = 0
    mock_monitor.y = 0
    mock_get_monitors.return_value = [mock_monitor]
    
    config = Configuration([mock_monitor])
    config._Configuration__config = {}
    config._Configuration__current_profile = 'profile_test'
    config._Configuration__config_file = tempfile.mktemp()
    config._Configuration__config['profile_test'] = {
      'DP-1': {'offsetX': 999.0, 'offsetY': 888.0}
    }
    
    populate_profile(config)
    
    # Should not overwrite existing section
    profile = config._Configuration__config['profile_test']
    self.assertEqual(profile['DP-1']['offsetX'], 999.0)
    self.assertEqual(profile['DP-1']['offsetY'], 888.0)

  @patch('src.spanned_image.screeninfo.get_monitors')
  @patch('src.spanned_image.find_config_file')
  def test_populate_profile_handles_none_monitor_name(self, mock_find_config, mock_get_monitors):
    """Test that populate_profile handles monitors with None name."""
    mock_find_config.return_value = None
    mock_monitor = Mock(spec=Monitor)
    mock_monitor.name = None
    mock_monitor.x = 0
    mock_monitor.y = 0
    mock_get_monitors.return_value = [mock_monitor]
    
    config = Configuration([mock_monitor])
    config._Configuration__config = {}
    config._Configuration__current_profile = 'profile_test'
    config._Configuration__config_file = tempfile.mktemp()
    config._Configuration__config['profile_test'] = {}
    
    populate_profile(config)
    
    # Should not create a section for monitor with None name
    profile = config._Configuration__config['profile_test']
    self.assertEqual(len(profile), 0)


if __name__ == '__main__':
  unittest.main()
