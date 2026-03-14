#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import configparser
import shutil
import datetime
import subprocess

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LANG'] = 'en_US.UTF-8'

if sys.version_info[0] >= 3:
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stdin.reconfigure(encoding='utf-8')
    except Exception:
        pass

TELEGRAF_DIR = "/etc/telegraf/telegraf.d/tgw"
SCRIPTS_DIR = "/opt/scripts/telegraf/tgwMonitor"
SCRIPTS_TGW_MONITOR_368 = os.path.join(SCRIPTS_DIR, "tgwMonitor_3.6.8.py")
SCRIPTS_TGW_MONITOR = os.path.join(SCRIPTS_DIR, "tgwMonitor.py")
TEMPLATE_FILE = os.path.join(SCRIPTS_DIR, "config.ini.template")

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

def backup_file(filepath):
    if os.path.exists(filepath):
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        backup_path = "{}.{}".format(filepath, timestamp)
        shutil.copy2(filepath, backup_path)
        return backup_path
    return None

def backup_and_write(filepath, content):
    backup_file(filepath)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def read_template():
    with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        return f.read()

def generate_ini_content(tgw_ip, tgw_port, tgw_monitor_password, tgw_id, platforms, interval):
    template = read_template()
    content = template.replace('{{ tgw_ip }}', tgw_ip)
    content = content.replace('{{ tgw_port }}', str(tgw_port))
    content = content.replace('{{ tgw_monitor_password }}', tgw_monitor_password)
    content = content.replace('{{ tgw_id }}', tgw_id)
    content = content.replace('{{ platforms }}', platforms)
    content = content.replace('{{ interval }}', str(interval))
    return content

def generate_telegraf_conf(tgw_id, node):
    script_path = SCRIPTS_TGW_MONITOR_368 if USE_368 else SCRIPTS_TGW_MONITOR
    config_path = os.path.join(SCRIPTS_DIR, "{}.ini".format(tgw_id))
    conf_content = """[[inputs.execd]]
  interval = "30s"
  command = ["/usr/bin/python3", "{}", "-c", "{}"]
  data_format = "influx"
  [inputs.execd.tags]
    node = "{}"
""".format(script_path, config_path, node)
    return conf_content

def get_python_version():
    version_info = sys.version_info
    return version_info.major * 10 + version_info.minor

def check_python_version():
    version = get_python_version()
    if version >= 38:
        return "3.8+"
    elif version >= 36:
        return "3.6.8"
    return "unknown"

def get_script_version():
    version = get_python_version()
    if version >= 38:
        return "3.8+"
    elif version >= 36:
        return "3.6.8"
    return "unknown"

USE_368 = False

def add_or_update(tgw_id, tgw_ip, tgw_port, tgw_monitor_password, platforms, interval, node, reload=False):
    ensure_dir(TELEGRAF_DIR)
    ensure_dir(SCRIPTS_DIR)

    ini_path = os.path.join(SCRIPTS_DIR, "{}.ini".format(tgw_id))
    ini_content = generate_ini_content(tgw_ip, tgw_port, tgw_monitor_password, tgw_id, platforms, interval)
    backup_and_write(ini_path, ini_content)
    print("[+] Config file generated: {}".format(ini_path))

    conf_path = os.path.join(TELEGRAF_DIR, "{}.conf".format(tgw_id))
    disabled_path = os.path.join(TELEGRAF_DIR, "{}.conf.disabled".format(tgw_id))

    if os.path.exists(disabled_path):
        os.rename(disabled_path, conf_path)
        print("[+] Enabled from disabled: {}".format(conf_path))
    else:
        conf_content = generate_telegraf_conf(tgw_id, node)
        backup_and_write(conf_path, conf_content)
        print("[+] Telegraf config generated: {}".format(conf_path))

    if reload:
        reload_telegraf()

def enable(tgw_id, reload=False):
    conf_path = os.path.join(TELEGRAF_DIR, "{}.conf".format(tgw_id))
    disabled_path = os.path.join(TELEGRAF_DIR, "{}.conf.disabled".format(tgw_id))

    if os.path.exists(conf_path):
        print("[*] Config already exists, no need to enable: {}".format(conf_path))
        return

    if os.path.exists(disabled_path):
        os.rename(disabled_path, conf_path)
        print("[+] Enabled: {}".format(conf_path))
        if reload:
            reload_telegraf()
    else:
        print("[-] Config not found: {}".format(tgw_id))

def disable(tgw_id, reload=False):
    conf_path = os.path.join(TELEGRAF_DIR, "{}.conf".format(tgw_id))
    disabled_path = os.path.join(TELEGRAF_DIR, "{}.conf.disabled".format(tgw_id))

    if os.path.exists(conf_path):
        os.rename(conf_path, disabled_path)
        print("[+] Disabled: {}".format(disabled_path))
        if reload:
            reload_telegraf()
    elif os.path.exists(disabled_path):
        print("[*] Already disabled: {}".format(disabled_path))
    else:
        print("[-] Config not found: {}".format(tgw_id))

def reload_telegraf():
    try:
        subprocess.run(["systemctl", "reload", "telegraf"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[+] Telegraf config reloaded")
    except Exception:
        print("[*] Cannot reload telegraf, skipped")

def update_config(tgw_id, tgw_ip=None, tgw_port=None, tgw_monitor_password=None, platforms=None, interval=None, reload=False):
    ini_path = os.path.join(SCRIPTS_DIR, "{}.ini".format(tgw_id))
    
    if not os.path.exists(ini_path):
        print("[-] INI config not found: {}".format(ini_path))
        return

    config = configparser.ConfigParser()
    config.read(ini_path, encoding='utf-8')

    if tgw_ip is not None:
        config.set('gateway', 'host', tgw_ip)
    if tgw_port is not None:
        config.set('gateway', 'port', tgw_port)
    if tgw_monitor_password is not None:
        config.set('gateway', 'password', tgw_monitor_password)
    if platforms is not None:
        config.set('gateway', 'required_platforms', platforms)
    if interval is not None:
        config.set('collector', 'interval', interval)

    backup_and_write(ini_path, '')
    with open(ini_path, 'w', encoding='utf-8') as f:
        config.write(f)

    print("[+] INI config updated: {}".format(ini_path))

    if reload:
        reload_telegraf()

def list_configs():
    tgw_ids = set()

    if os.path.exists(TELEGRAF_DIR):
        for f in os.listdir(TELEGRAF_DIR):
            if f.endswith('.conf'):
                tgw_id = f.replace('.conf', '')
                tgw_ids.add(tgw_id)
            elif f.endswith('.conf.disabled'):
                tgw_id = f.replace('.conf.disabled', '')
                tgw_ids.add(tgw_id)

    if os.path.exists(SCRIPTS_DIR):
        for f in os.listdir(SCRIPTS_DIR):
            if f.endswith('.ini'):
                tgw_id = f.replace('.ini', '')
                tgw_ids.add(tgw_id)

    print("\n{:<20} {:<15} {:<25}".format("TGW_ID", "INI Config", "Telegraf Config"))
    print("-" * 60)

    for tgw_id in sorted(tgw_ids):
        ini_path = os.path.join(SCRIPTS_DIR, "{}.ini".format(tgw_id))
        conf_path = os.path.join(TELEGRAF_DIR, "{}.conf".format(tgw_id))
        disabled_path = os.path.join(TELEGRAF_DIR, "{}.conf.disabled".format(tgw_id))

        ini_status = "Exists" if os.path.exists(ini_path) else "Not Found"

        if os.path.exists(conf_path):
            telegraf_status = "Enabled"
        elif os.path.exists(disabled_path):
            telegraf_status = "Disabled"
        else:
            telegraf_status = "Not Found"

        print("{:<20} {:<15} {:<25}".format(tgw_id, ini_status, telegraf_status))

def interactive_mode():
    print("\n=== TGW Monitor Config Management ===")
    print("1. Add/Update config")
    print("2. Update INI config only")
    print("3. Enable config")
    print("4. Disable config")
    print("5. List configs")
    print("6. Exit")

    choice = input("\nSelect operation: ").strip()

    if choice == '1':
        tgw_id = input("Enter tgw_id: ").strip()
        tgw_ip = input("Enter tgw_ip: ").strip()
        tgw_port = input("Enter tgw_port: ").strip()
        tgw_monitor_password = input("Enter tgw_monitor_password: ").strip()
        platforms = input("Enter platforms (comma separated, default 1,2,3,4,5,6): ").strip() or "1,2,3,4,5,6"
        interval = input("Enter interval (default 10): ").strip() or "10"
        node = input("Enter node: ").strip()

        if not all([tgw_id, tgw_ip, tgw_port, tgw_monitor_password, platforms, node]):
            print("[-] Parameters cannot be empty")
            return

        reload_flag = input("Reload telegraf? (y/N): ").strip().lower() == 'y'
        add_or_update(tgw_id, tgw_ip, tgw_port, tgw_monitor_password, platforms, interval, node, reload_flag)

    elif choice == '2':
        tgw_id = input("Enter tgw_id: ").strip()
        tgw_ip = input("Enter tgw_ip (leave empty to skip): ").strip() or None
        tgw_port = input("Enter tgw_port (leave empty to skip): ").strip() or None
        tgw_monitor_password = input("Enter tgw_monitor_password (leave empty to skip): ").strip() or None
        platforms = input("Enter platforms (leave empty to skip): ").strip() or None
        interval = input("Enter interval (leave empty to skip): ").strip() or None

        reload_flag = input("Reload telegraf? (y/N): ").strip().lower() == 'y'
        update_config(tgw_id, tgw_ip, tgw_port, tgw_monitor_password, platforms, interval, reload_flag)

    elif choice == '3':
        tgw_id = input("Enter tgw_id: ").strip()
        reload_flag = input("Reload telegraf? (y/N): ").strip().lower() == 'y'
        enable(tgw_id, reload_flag)

    elif choice == '4':
        tgw_id = input("Enter tgw_id: ").strip()
        reload_flag = input("Reload telegraf? (y/N): ").strip().lower() == 'y'
        disable(tgw_id, reload_flag)

    elif choice == '5':
        list_configs()

    elif choice == '6':
        sys.exit(0)
    else:
        print("[-] Invalid selection")

def main():
    global USE_368

    version = get_python_version()
    if version < 36:
        print("[-] Unsupported Python version, requires 3.6.8 or higher")
        sys.exit(1)
    USE_368 = (version < 38)

    parser = argparse.ArgumentParser(description='TGW Monitor Config Management Tool')
    parser.add_argument('-a', '--add', action='store_true', help='Add or update config')
    parser.add_argument('-u', '--update', action='store_true', help='Update INI config (use with --tgw_id and other options)')
    parser.add_argument('-e', '--enable', metavar='TGW_ID', help='Enable config')
    parser.add_argument('-d', '--disable', metavar='TGW_ID', help='Disable config')
    parser.add_argument('-l', '--list', action='store_true', help='List configs')
    parser.add_argument('-i', '--interactive', action='store_true', help='Interactive mode')
    parser.add_argument('--tgw_id', metavar='ID', help='TGW ID')
    parser.add_argument('--tgw_ip', metavar='IP', help='TGW IP address')
    parser.add_argument('--tgw_port', metavar='PORT', help='TGW port')
    parser.add_argument('--password', metavar='PWD', help='TGW monitor password')
    parser.add_argument('--platforms', metavar='PLATFORMS', help='Platform IDs (comma separated)')
    parser.add_argument('--interval', metavar='INTERVAL', default='10', help='Collection interval (seconds)')
    parser.add_argument('--node', metavar='NODE', help='Business node')
    parser.add_argument('-r', '--reload', action='store_true', help='Reload telegraf after operation')

    args = parser.parse_args()

    if args.interactive or not any([args.add, args.update, args.enable, args.disable, args.list]):
        interactive_mode()
        return

    if args.list:
        list_configs()
        return

    if args.add:
        if not all([args.tgw_id, args.tgw_ip, args.tgw_port, args.password, args.platforms, args.node]):
            print("[-] Add config requires all parameters: --tgw_id, --tgw_ip, --tgw_port, --password, --platforms, --node")
            sys.exit(1)
        add_or_update(args.tgw_id, args.tgw_ip, args.tgw_port, args.password, args.platforms, args.interval, args.node, args.reload)
        return

    if args.update:
        if args.tgw_id is None:
            print("[-] Update config requires --tgw_id")
            sys.exit(1)
        update_config(args.tgw_id, args.tgw_ip, args.tgw_port, args.password, args.platforms, args.interval, args.reload)
        return

    if args.enable:
        enable(args.enable, args.reload)
        return

    if args.disable:
        disable(args.disable, args.reload)
        return

    parser.print_help()
    interactive_mode()

if __name__ == '__main__':
    main()
