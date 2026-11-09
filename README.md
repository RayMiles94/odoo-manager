# odoo-manager

Restore an Odoo backup zip (`dump.sql` + `filestore/`) from the command line, using Odoo's own
`restore_db`. Works with Odoo 15 to 19. Extraction uses `~/tmp_restore` instead of `/tmp`
(which can be a small RAM-backed tmpfs).

## Install

Inside the same virtualenv you use for Odoo:

```bash
pip install git+https://github.com/<your-user>/odoo-manager.git
```

Odoo itself is not a pip dependency: the tool imports it from the folder of the `odoo-bin` you give.

## Usage

Without a config file:

```bash
odoo-manager /path/to/odoo-bin /path/to/odoo.conf /path/to/db.zip --db mydb --force
```

With a config file providing `odoo_bin` and `odoo_conf`, the command is shorter:

```bash
odoo-manager db.zip --db mydb --force
```

## Config file

JSON with three optional keys: `odoo_bin`, `odoo_conf`, `tmp_dir`. Lookup order (first found wins):

1. `--config /path/file.json`
2. `./odoo_manager.json`
3. `~/.config/odoo-manager/config.json`

```json
{
    "odoo_bin": "~/Documents/odoo/odoo_15/odoo/odoo-bin",
    "odoo_conf": "~/Documents/odoo/odoo_15/odoo.conf",
    "tmp_dir": "~/tmp_restore"
}
```

Create it automatically from one full run:

```bash
odoo-manager /path/odoo-bin /path/odoo.conf db.zip --db mydb --save-config
```

Command-line values always override the config file.

## Options

| Option | Meaning |
|---|---|
| `--db NAME` | Target DB name (default: zip name without extension) |
| `--force` | Drop the target DB if it exists |
| `--neutralize` | Neutralize after restore (Odoo 16+) |
| `--tmp-dir DIR` | Extraction directory |
| `--config FILE` | Config file path |
| `--save-config` | Save the paths used in this run |

## Note

A backup made with the "pg_dump" option has no filestore, so images and attachments will be missing.
