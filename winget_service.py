import subprocess


CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW


def run_winget_command(arguments):
    result = subprocess.run(
        ["winget", *arguments],
        capture_output=True,
        text=True,
        creationflags=CREATE_NO_WINDOW
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or "WinGet command failed."
        )

    return result.stdout

def check_winget_connectivity():
    result = subprocess.run(
        [
            "winget",
            "source",
            "update"
        ],
        capture_output=True,
        text=True,
        creationflags=CREATE_NO_WINDOW
    )

    output = (
        result.stdout.strip()
        + "\n"
        + result.stderr.strip()
    ).strip()

    if result.returncode != 0:
        return False, output

    failure_phrases = (
        "failed",
        "error",
        "unable",
        "network",
        "internet",
        "connection",
        "source data is missing"
    )

    lowered = output.lower()

    if any(
        phrase in lowered
        for phrase in failure_phrases
    ):
        return False, output

    return True, output

def get_available_updates():
    return run_winget_command([
        "list",
        "--upgrade-available",
        "--accept-source-agreements"
    ])

def update_all():
    return run_winget_command([
        "upgrade",
        "--all",
        "--accept-source-agreements",
        "--accept-package-agreements"
    ])