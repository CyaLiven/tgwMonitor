#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="${SCRIPT_DIR}/manage_tgwMonitor.py"

usage() {
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  add|new          Add or update TGW monitor configuration"
    echo "  update|up        Update INI config only"
    echo "  enable           Enable TGW monitor"
    echo "  disable          Disable TGW monitor"
    echo "  list             List all configurations"
    echo "  interactive|i    Enter interactive mode"
    echo ""
    echo "Options for 'add':"
    echo "  --tgw_id <id>         TGW ID (required)"
    echo "  --tgw_ip <ip>        TGW IP address (required)"
    echo "  --tgw_port <port>    TGW port (required)"
    echo "  --password <pwd>     TGW monitor password (required)"
    echo "  --platforms <ids>    Platform IDs, comma separated (required)"
    echo "  --interval <sec>     Collection interval in seconds (default: 10)"
    echo "  --node <node>        Business node (required)"
    echo ""
    echo "Options for 'update':"
    echo "  --tgw_id <id>         TGW ID (required)"
    echo "  --tgw_ip <ip>        TGW IP address (optional)"
    echo "  --tgw_port <port>    TGW port (optional)"
    echo "  --password <pwd>     TGW monitor password (optional)"
    echo "  --platforms <ids>    Platform IDs, comma separated (optional)"
    echo "  --interval <sec>     Collection interval in seconds (optional)"
    echo ""
    echo "Options for 'enable/disable':"
    echo "  --tgw_id <id>        TGW ID (required)"
    echo ""
    echo "Global Options:"
    echo "  -r, --reload         Reload telegraf after operation"
    echo ""
    echo "Examples:"
    echo "  $0 add --tgw_id W123456Y0001 --tgw_ip 192.168.1.100 --tgw_port 7000 --password secret --platforms 1,2,3 --node beijing"
    echo "  $0 add --tgw_id W123456Y0001 --tgw_ip 192.168.1.100 --tgw_port 7000 --password secret --platforms 1,2,3 --node beijing -r"
    echo "  $0 update --tgw_id W123456Y0001 --tgw_ip 192.168.1.200"
    echo "  $0 update --tgw_id W123456Y0001 --interval 20 -r"
    echo "  $0 enable --tgw_id W123456Y0001"
    echo "  $0 disable --tgw_id W123456Y0001 -r"
    echo "  $0 list"
    echo "  $0 interactive"
}

if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: Python script not found: $PYTHON_SCRIPT"
    exit 1
fi

COMMAND="$1"

case "$COMMAND" in
    add|new)
        shift
        python3 "$PYTHON_SCRIPT" -a "$@"
        ;;
    update|up)
        shift
        python3 "$PYTHON_SCRIPT" -u "$@"
        ;;
    enable)
        shift
        ARGS=""
        while [[ $# -gt 0 ]]; do
            if [[  $1 = '--tgw_id']];then
                shift
                ARGS="$ARGS $1"
                shift
            fi
            ARGS="$ARGS $1"
            shift
        done
        python3 "$PYTHON_SCRIPT" -e $ARGS
        ;;
    disable)
        shift
        ARGS=""
        while [[ $# -gt 0 ]]; do
            if [[  $1 = '--tgw_id']];then
                shift
                ARGS="$ARGS $1"
                shift
            fi
            ARGS="$ARGS $1"
            shift
        done
        python3 "$PYTHON_SCRIPT" -d $ARGS
        ;;
    list)
        shift
        python3 "$PYTHON_SCRIPT" -l "$@"
        ;;
    interactive|i)
        python3 "$PYTHON_SCRIPT" -i
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        if [ -z "$COMMAND" ]; then
            python3 "$PYTHON_SCRIPT" -i
        else
            echo "Unknown command: $COMMAND"
            usage
            exit 1
        fi
        ;;
esac
