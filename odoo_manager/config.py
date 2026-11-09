"""Optional JSON config file for odoo-manager.

Example (odoo_manager.json):
    {
        "odoo_bin": "~/Documents/odoo/odoo_15/odoo/odoo-bin",
        "odoo_conf": "~/Documents/odoo/odoo_15/odoo.conf",
        "tmp_dir": "~/tmp_restore"
    }

Lookup order (first file found wins):
    1. the path given with --config
    2. ./odoo_manager.json (current directory)
    3. $XDG_CONFIG_HOME/odoo-manager/config.json (default ~/.config/odoo-manager/config.json)
"""
import json
import os
import sys

CONFIG_NAME = "odoo_manager.json"
KEYS = ("odoo_bin", "odoo_conf", "tmp_dir")


def user_config_path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "odoo-manager", "config.json")


def candidate_paths(explicit=None):
    if explicit:
        return [os.path.expanduser(explicit)]
    return [os.path.join(os.getcwd(), CONFIG_NAME), user_config_path()]


def load_config(explicit=None):
    """Return (config_dict, path_used). (({}, None) when no file exists)."""
    for path in candidate_paths(explicit):
        if not os.path.isfile(path):
            if explicit:
                sys.exit(f"Error: config file not found: {path}")
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as exc:
            sys.exit(f"Error: cannot read config file {path}: {exc}")
        if not isinstance(data, dict):
            sys.exit(f"Error: config file {path} must contain a JSON object.")
        cfg = {}
        for key, value in data.items():
            if key in KEYS and value:
                cfg[key] = os.path.abspath(os.path.expanduser(str(value)))
            elif key not in KEYS:
                print(f"Warning: unknown key '{key}' in {path} (ignored).", file=sys.stderr)
        return cfg, path
    return {}, None


def save_config(cfg, path=None):
    path = os.path.expanduser(path) if path else user_config_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({k: cfg[k] for k in KEYS if cfg.get(k)}, f, indent=4)
        f.write("\n")
    return path
