"""Builds the zip of the Alexa skill that is uploaded to AWS Lambda.

Run `python alexa_lambda/deployment_zip.py` from the repository root to write
`build/alexa_lambda.zip`. The zip holds `bridge_skill`, every module in `shared` and
`tzdata`, so the Lambda has no dependency on the machine it was built on. `boto3` is
omitted because the AWS Lambda Python runtime already provides it.
"""

from importlib.util import find_spec
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

_REPOSITORY_ROOT = Path(__file__).parents[1]
_DEFAULT_DESTINATION = _REPOSITORY_ROOT / "build" / "alexa_lambda.zip"

# The permissions of each file in the zip. AWS Lambda runs as another user, so it can
# only read files that everyone can.
_FILE_PERMISSIONS = 0o644


def _package_files(package_directory: Path) -> dict[Path, str]:
    """Maps every file of a package to where it sits inside the zip.

    Args:
        package_directory: The directory of the package.

    Returns:
        The path of each file, excluding cached bytecode, mapped to its path inside a
        zip that holds the package at its top level.
    """
    return {
        path: path.relative_to(package_directory.parent).as_posix()
        for path in package_directory.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }


def _find_tzdata_directory() -> Path:
    """Finds the `tzdata` package installed in the active environment.

    Returns:
        The directory of the installed `tzdata` package.

    Raises:
        ModuleNotFoundError: If `tzdata` is not installed.
    """
    spec = find_spec("tzdata")

    if spec is None or spec.origin is None:
        raise ModuleNotFoundError("`tzdata` is not installed.")

    return Path(spec.origin).parent


def build_deployment_zip(destination: Path) -> None:
    """Writes the zip of the Alexa skill that is uploaded to AWS Lambda.

    Args:
        destination: The path to write the zip to. A zip already there is replaced.
    """
    archive_paths = (
        _package_files(_REPOSITORY_ROOT / "alexa_lambda" / "bridge_skill")
        | {path: path.name for path in (_REPOSITORY_ROOT / "shared").glob("*.py")}
        | _package_files(_find_tzdata_directory())
    )

    destination.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(destination, "w") as archive:
        for path, archive_path in archive_paths.items():
            info = ZipInfo.from_file(path, archive_path)
            info.external_attr = _FILE_PERMISSIONS << 16

            archive.writestr(info, path.read_bytes(), compress_type=ZIP_DEFLATED)


def main() -> None:
    """Writes the zip of the Alexa skill to its default destination."""
    build_deployment_zip(_DEFAULT_DESTINATION)

    print(f"Wrote {_DEFAULT_DESTINATION}")


if __name__ == "__main__":
    main()
