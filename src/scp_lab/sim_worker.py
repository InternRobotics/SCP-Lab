"""Private child-process entry point. Receives only code emitted by our compiler."""

import contextlib
import importlib.metadata
import io
import json
import sys


def main():
    output = io.StringIO()
    result = {}
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        try:
            from opentrons.simulate import simulate

            version = importlib.metadata.version("opentrons")
            if version != "8.8.2":
                raise RuntimeError(f"Expected Opentrons 8.8.2, found {version}")
            with open(sys.argv[1], encoding="utf-8") as stream:
                runlog, _ = simulate(stream, file_name="scp_lab_generated.py")
            result = {
                "status": "succeeded",
                "sdk_version": version,
                "command_count": len(runlog),
                "commands": [
                    {"level": entry["level"], "text": str(entry["payload"]["text"])}
                    for entry in runlog[:10000]
                ],
                "commands_truncated": len(runlog) > 10000,
            }
        except Exception as error:
            result = {"status": "failed", "error_type": type(error).__name__, "error": str(error)}
    result["diagnostics"] = output.getvalue()[-20000:]
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
