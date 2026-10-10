import argparse
import json
import sys
from pathlib import Path

from .capabilities import list_capabilities, protocol_schema
from .client_config import make_client_config
from .compiler import compile_protocol
from .models import Protocol
from .simulation import get_run, simulate_protocol
from .validation import validate


def main():
    parser = argparse.ArgumentParser(description="SCP-Lab device access reference implementation")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("capabilities", "schema"):
        commands.add_parser(name)
    for name in ("serve", "devices", "check", "device"):
        command = commands.add_parser(name)
        command.add_argument(
            "--devices-dir", type=Path, help="Device JSON directory; replaces demos"
        )
        if name == "device":
            command.add_argument("device_id")
    for name in ("validate", "compile", "simulate"):
        command = commands.add_parser(name)
        command.add_argument("protocol", type=Path)
        if name == "compile":
            command.add_argument("--output", "-o", type=Path)
    commands.add_parser("run").add_argument("run_id")
    config_command = commands.add_parser(
        "mcp-config", help="Generate local MCP stdio configuration"
    )
    config_command.add_argument("--project-dir", type=Path, default=Path.cwd())
    config_command.add_argument("--simulation-python", type=Path)
    config_command.add_argument("--devices-dir", type=Path)
    config_command.add_argument("--output", "-o", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "serve":
            from .server import main as serve

            return serve(args.devices_dir)
        if args.command == "mcp-config":
            result = make_client_config(args.project_dir, args.simulation_python, args.devices_dir)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(
                    json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
                )
        elif args.command in ("devices", "device", "check"):
            from .registry import create_runtime

            runtime = create_runtime(args.devices_dir)
            if args.command == "check":
                from .conformance import check_runtime

                result = check_runtime(runtime)
            elif args.command == "devices":
                result = runtime.list_devices()
            else:
                result = runtime.describe_device(args.device_id)
        elif args.command == "capabilities":
            result = list_capabilities()
        elif args.command == "schema":
            result = protocol_schema()
        elif args.command == "run":
            result = get_run(args.run_id)
        else:
            protocol = Protocol.model_validate_json(args.protocol.read_text(encoding="utf-8"))
            if args.command == "validate":
                result = validate(protocol)
            elif args.command == "compile":
                result = compile_protocol(protocol)
                if args.output:
                    args.output.parent.mkdir(parents=True, exist_ok=True)
                    args.output.write_text(result["code"], encoding="utf-8")
                    result = {"output": str(args.output), "validation": result["validation"]}
                else:
                    print(result["code"], end="")
                    return
            else:
                result = simulate_protocol(protocol)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if isinstance(result, dict) and result.get("status") in ("failed", "unavailable"):
            sys.exit(1)
    except (ValueError, OSError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
