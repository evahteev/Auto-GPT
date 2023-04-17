"""Handles loading of plugins."""
import importlib
import mimetypes
import os
import zipfile
from modulefinder import Module
from pathlib import Path
from typing import List
from typing import Optional, Tuple
from zipimport import zipimporter

import json

import openapi_python_client
import typer
import yaml
from openapi_python_client.cli import _process_config, Config as OpenAPIConfig

from scripts.config import Config


def inspect_zip_for_module(zip_path: str, debug: bool = False) -> Optional[str]:
    """
    Inspect a zipfile for a module.

    Args:
        zip_path (str): Path to the zipfile.
        debug (bool, optional): Enable debug logging. Defaults to False.

    Returns:
        Optional[str]: The name of the module if found, else None.
    """
    with zipfile.ZipFile(zip_path, 'r') as zfile:
        for name in zfile.namelist():
            if name.endswith("__init__.py"):
                if debug:
                    print(f"Found module '{name}' in the zipfile at: {name}")
                return name
    if debug:
        print(f"Module '__init__.py' not found in the zipfile @ {zip_path}.")
    return None


def scan_plugins(plugins_path: Path, debug: bool = False, plugins_type: str = 'generic'):
    """Scan the plugins directory for plugins.

    Args:
        plugins_path (Path): Path to the plugins directory.

    Returns:
        List[Path]: List of plugins.
    """
    plugins = {}
    if plugins_type == 'generic':
        if not plugins_path.is_dir():
            raise ValueError(f"{plugins_path} is not a directory")
        for item in plugins_path.iterdir():
            if item.is_dir():
                for plugin in item.glob("*.zip"):
                    if module := inspect_zip_for_module(str(plugin), debug):
                        plugin_name = os.path.basename(os.path.normpath(item))
                        plugins[plugin_name] = {
                            'module': module,
                            'plugin': plugin,
                            'plugin_type': 'generic'
                        }
    elif plugins_type == 'openai':
        if not plugins_path.is_dir():
            raise ValueError(f"{plugins_path} is not a directory")
        for item in plugins_path.iterdir():
            if item.is_dir():
                print(f"Folder: {item}")
                manifest = None
                for config in item.glob("manifest.json"):
                    json_data = config.read_text()
                    manifest = json.loads(json_data)
                for config in item.glob("openapi.*"):
                    yaml_bytes = config.read_bytes()
                    content_type = mimetypes.guess_type(config.absolute().as_uri(), strict=True)[0]
                    openapi_spec = openapi_python_client._load_yaml_or_json(yaml_bytes, content_type)
                    _meta_option = openapi_python_client.MetaType.SETUP,
                    _config = OpenAPIConfig(**{
                        'project_name_override': 'client',
                        'package_name_override': 'client',
                    })
                    prev_cwd = Path.cwd()
                    os.chdir(item)
                    openapi_python_client.create_new_client(url=None, path=config, meta=_meta_option, config=_config)

                    spec = importlib.util.spec_from_file_location('client', 'client/client/client.py')
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    client = module.Client(base_url=openapi_spec.servers[0].url)
                    os.chdir(prev_cwd)
                plugin_name = os.path.basename(os.path.normpath(item))
                plugins[plugin_name] = {
                    'manifest': manifest,
                    'openapi_spec': openapi_spec,
                    'client': client,
                    'plugin_type': 'openai'
                }

    return plugins


def load_generic_plugins(plugins_path: Path, debug: bool = False) -> List[Module]:
    """Load plugins from the generic plugins directory.

    Args:
        plugins_path (Path): Path to the plugins directory.

    Returns:
        List[Path]: List of plugins.
    """
    plugins = scan_plugins(plugins_path, plugins_type='generic')
    plugin_modules = []
    for module, plugin in plugins:
        plugin = Path(plugin)
        module = Path(module)
        if debug:
            print(f"Plugin: {plugin} Module: {module}")
        zipped_package = zipimporter(plugin)
        zipped_module = zipped_package.load_module(str(module.parent))
        for key in dir(zipped_module):
            if key.startswith("__"):
                continue
            a_module = getattr(zipped_module, key)
            a_keys = dir(a_module)
            if '_abc_impl' in a_keys and \
                    a_module.__name__ != 'AutoGPTPluginTemplate':
                plugin_modules.append(a_module)
    return plugin_modules


def load_openai_plugins(plugins_path: Path, debug: bool = False) -> List[Module]:
    """Load plugins from the openai plugins directory.

    Args:
        plugins_path (Path): Path to the plugins directory.

    Returns:
        List[Path]: List of plugins.
    """
    plugins = scan_plugins(plugins_path, plugins_type='openai')
    return plugins


def _init_generic_plugins(plugins_path: Path, cfg: Config, debug: bool = False) -> List[Module]:
    """Initialize generic plugins."""
    plugins_found = load_generic_plugins(Path(os.getcwd()) / plugins_path / "generic")
    loaded_plugins = []
    for plugin in plugins_found:
        if plugin.__name__ in cfg.plugins_blacklist:
            continue
        if plugin.__name__ in cfg.plugins_whitelist:
            loaded_plugins.append(plugin())
        else:
            ack = input(
                f"WARNNG Plugin {plugin.__name__} found. But not in the"
                " whitelist... Load? (y/n): "
            )
            if ack.lower() == "y":
                loaded_plugins.append(plugin())

    if loaded_plugins:
        print(f"\nPlugins found: {len(loaded_plugins)}\n"
              "--------------------")
    for plugin in loaded_plugins:
        print(f"{plugin._name}: {plugin._version} - {plugin._description}")

    return loaded_plugins


def _init_openai_plugins(plugins_path: Path, cfg: Config, debug: bool = False) -> List[Module]:
    """Initialize OpenAI plugins."""
    plugins_found = load_openai_plugins(Path(os.getcwd()) / plugins_path / "openai")
    loaded_plugins = []
    for plugin_name,  plugin_spec in plugins_found.items():
        if plugin_name in cfg.plugins_blacklist:
            continue
        if plugin_name in cfg.plugins_whitelist:
            loaded_plugins.append(plugin_spec)
        else:
            ack = input(
                f"WARNNG Plugin {plugin_name} found. But not in the"
                " whitelist... Load? (y/n): "
            )
            if ack.lower() == "y":
                loaded_plugins.append(plugin_spec)
    return loaded_plugins


def init_plugins(plugins_path, cfg: Config, debug: bool = False) -> List[Module]:
    """Initialize plugins."""

    loaded_openai_plugins = _init_openai_plugins(plugins_path, cfg, debug)
    loaded_plugins = _init_generic_plugins(plugins_path, cfg, debug)
    cfg.set_plugins(loaded_plugins)
    return cfg
