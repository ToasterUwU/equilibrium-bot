__all__ = ["format_every_string", "load_help_command_assets", "generate_help_command_pages"]


import os
from typing import Dict

from internal_tools.discord import fancy_embed


def format_every_string(data: dict, **kwargs):
    new_data = {}

    for key, sub_data in data.items():
        if isinstance(key, str):
            key = key.format_map(kwargs)

        if isinstance(sub_data, dict):
            sub_data = format_every_string(sub_data, **kwargs)

        if isinstance(sub_data, str):
            sub_data = sub_data.format_map(kwargs)

        new_data[key] = sub_data

    return new_data


def load_help_command_assets(path: str) -> Dict[int, Dict[str, str]]:
    help_command_assets = {}

    for x in os.scandir(path):
        if x.is_dir():
            index = int(x.name)
            help_command_assets[index] = {}

            for y in os.scandir(x.path):
                if y.is_file():
                    with open(y.path, "r", encoding="utf-8") as f:
                        help_command_assets[index][
                            y.name.replace(".txt", "")
                        ] = f.read()

    help_command_assets = dict(sorted(help_command_assets.items()))

    return help_command_assets


def generate_help_command_pages(
    help_command_assets: Dict[int, Dict[str, str]], **kwargs
):
    return [
        fancy_embed(**x)
        for x in format_every_string(help_command_assets, kwargs=kwargs).values()
    ]
