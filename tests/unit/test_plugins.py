import os
from pathlib import Path
from typing import List

import pytest

from scripts.config import Config
# Import your functions here
from scripts.plugins import inspect_zip_for_module, scan_plugins, load_generic_plugins, load_openai_plugins, \
    init_plugins


@pytest.fixture
def config():
    return Config()


class TestPluginLoader:

    def test_inspect_zip_for_module(self):
        # Test when the module is found
        test_zip_path = 'path/to/your/test/zipfile.zip'
        result = inspect_zip_for_module(test_zip_path)
        assert result is not None
        assert result.endswith('__init__.py')

        # Test when the module is not found
        test_invalid_zip_path = 'path/to/your/invalid/zipfile.zip'
        result = inspect_zip_for_module(test_invalid_zip_path)
        assert result is None

    def test_init_plugins(self, config: Config):
        plugins_path = Path('plugins')
        result = init_plugins(plugins_path, config)

        # Check if the result is a list
        assert isinstance(result, List)

    def test_scan_plugins(self):
        plugins_path = Path('plugins')
        result = scan_plugins(plugins_path)

        # Check if the result is a list
        assert isinstance(result, List)

        # Check if each item in the list is a tuple with two elements
        for plugin in result:
            assert isinstance(plugin, tuple)
            assert len(plugin) == 2
