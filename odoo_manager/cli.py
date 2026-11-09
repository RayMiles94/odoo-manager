import argparse
import inspect
import os
import sys
import tempfile

from . import __version__
from .config import load_config, save_config

DEFAULT_TMP_DIR = os.path.join(os.path.expanduser("~"), "tmp_restore")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="odoo-manager",
        description="Import an Odoo database backup (zip with dump.sql + filestore).",
        epilog=(
            "With a config file providing odoo_bin and odoo_conf, only the zip is needed:\n"
            "  odoo-manager db.zip --db mydb --force\n"
            "Without it:\n"
            "  odoo-manager /path/odoo-bin /path/odoo.conf db.zip --db mydb --force"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("paths", nargs="+", metavar="PATH",
                        help="DB_ZIP (when odoo_bin/odoo_conf come from the config file) "
                             "or ODOO_BIN ODOO_CONF DB_ZIP")
    parser.add_argument("--db", help="Target DB name (default: zip file name without extension)")
    parser.add_argument("--force", action="store_true",
                        help="Drop the target DB if it already exists")
    parser.add_argument("--neutralize", action="store_true",
                        help="Neutralize the DB after restore (Odoo 16+ only)")
    parser.add_argument("--tmp-dir",
                        help="Temporary extraction directory (default: config tmp_dir, "
                             "else ~/tmp_restore)")
    parser.add_argument("--config", help="Path to a JSON config file")
    parser.add_argument("--save-config", action="store_true",
                        help="Save odoo_bin / odoo_conf / tmp_dir used in this run to the "
                             "config file (--config path, else ~/.config/odoo-manager/config.json)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def resolve(parser, args, cfg):
    paths = args.paths
    if len(paths) == 3:
        odoo_bin, odoo_conf, db_zip = paths
    elif len(paths) == 1:
        db_zip = paths[0]
        odoo_bin, odoo_conf = cfg.get("odoo_bin"), cfg.get("odoo_conf")
        missing = [n for n, v in (("odoo_bin", odoo_bin), ("odoo_conf", odoo_conf)) if not v]
        if missing:
            parser.error("missing " + " and ".join(missing) + " (no config file provides "
                         "them): pass ODOO_BIN ODOO_CONF DB_ZIP, or create a config file.")
    else:
        parser.error("expected DB_ZIP (with config file) or ODOO_BIN ODOO_CONF DB_ZIP")

    tmp_dir = args.tmp_dir or cfg.get("tmp_dir") or DEFAULT_TMP_DIR
    return (os.path.abspath(os.path.expanduser(odoo_bin)),
            os.path.abspath(os.path.expanduser(odoo_conf)),
            os.path.abspath(os.path.expanduser(db_zip)),
            os.path.abspath(os.path.expanduser(tmp_dir)))


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    cfg, cfg_path = load_config(args.config)
    odoo_bin, odoo_conf, db_zip, tmp_dir = resolve(parser, args, cfg)

    for label, path in (("odoo-bin", odoo_bin), ("odoo.conf", odoo_conf), ("db zip", db_zip)):
        if not os.path.isfile(path):
            sys.exit(f"Error: {label} not found: {path}")

    if args.save_config:
        saved = save_config({"odoo_bin": odoo_bin, "odoo_conf": odoo_conf,
                             "tmp_dir": args.tmp_dir and tmp_dir or cfg.get("tmp_dir")},
                            args.config)
        print(f"Config saved: {saved}")
    elif cfg_path:
        print(f"Using config: {cfg_path}")

    # Equivalent of: mkdir -p ~/tmp_restore && TMPDIR=$HOME/tmp_restore
    os.makedirs(tmp_dir, exist_ok=True)
    os.environ["TMPDIR"] = tmp_dir
    tempfile.tempdir = tmp_dir
    print(f"Using temporary directory: {tmp_dir}")

    # Make the odoo package importable (odoo-bin lives in the source root)
    sys.path.insert(0, os.path.dirname(odoo_bin))
    try:
        import odoo
        from odoo.service import db as db_service
    except ImportError as exc:
        sys.exit(f"Error: cannot import odoo from {os.path.dirname(odoo_bin)} ({exc}). "
                 "Run this command inside the venv used for Odoo.")

    odoo.tools.config.parse_config(["-c", odoo_conf])
    odoo.netsvc.init_logger()

    db_name = args.db or os.path.splitext(os.path.basename(db_zip))[0]

    try:
        if db_service.exp_db_exist(db_name):
            if not args.force:
                sys.exit(f"Error: database '{db_name}' already exists. "
                         "Use --force to drop it first.")
            print(f"Dropping existing database '{db_name}'...")
            db_service.exp_drop(db_name)

        print(f"Restoring '{db_zip}' into database '{db_name}'...")
        kwargs = {"copy": False}  # copy=False keeps the original database UUID

        if args.neutralize:
            if "neutralize_database" in inspect.signature(db_service.restore_db).parameters:
                kwargs["neutralize_database"] = True
            else:
                print("Warning: this Odoo version has no built-in neutralization "
                      "(added in 16.0); ignoring --neutralize.")

        db_service.restore_db(db_name, db_zip, **kwargs)
        print(f"Done: database '{db_name}' restored.")
    finally:
        # Remove the temp directory if empty (rmdir never deletes content)
        try:
            os.rmdir(tmp_dir)
            print(f"Removed empty temporary directory: {tmp_dir}")
        except OSError:
            pass


if __name__ == "__main__":
    main()
