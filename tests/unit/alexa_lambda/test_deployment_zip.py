from pathlib import Path
from unittest.mock import Mock, patch
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from deployment_zip import (
    _DEFAULT_DESTINATION,
    _FILE_PERMISSIONS,
    _find_tzdata_directory,
    _package_files,
    build_deployment_zip,
    main,
)

_DEPLOYMENT_ZIP_MODULE = "deployment_zip"

_SHARED_MODULE_TEXT = "shared module"
_SKILL_MODULE_TEXT = "skill module"
_TZDATA_TEXT = "time zones"


def _write_file(path: Path, text: str) -> None:
    """Writes a text file, creating the parent directories it is missing.

    Args:
        path: The path of the file to write.
        text: The text to write to the file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@pytest.fixture
def repository_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Fakes the repository a deployment zip is built from.

    Args:
        tmp_path: The temporary directory to build the repository in.
        monkeypatch: The fixture pointing `deployment_zip` at the fake repository.

    Returns:
        The root of a repository whose `shared` directory holds a Python module and a
        file that is not Python.
    """
    root = tmp_path / "repository"
    _write_file(root / "shared" / "bridge_closure.py", _SHARED_MODULE_TEXT)
    _write_file(root / "shared" / "notes.txt", "not python")

    monkeypatch.setattr(f"{_DEPLOYMENT_ZIP_MODULE}._REPOSITORY_ROOT", root)

    return root


@pytest.fixture
def skill_directory(repository_root: Path) -> Path:
    """Fakes the directory of the `bridge_skill` package.

    Args:
        repository_root: The root of the fake repository.

    Returns:
        A directory in the fake repository holding one module.
    """
    directory = repository_root / "alexa_lambda" / "bridge_skill"
    _write_file(directory / "lambda_function.py", _SKILL_MODULE_TEXT)

    return directory


@pytest.fixture
def tzdata_directory(tmp_path: Path) -> Path:
    """Fakes the directory of the installed `tzdata` package.

    Args:
        tmp_path: The temporary directory to build the package in.

    Returns:
        A directory holding one file.
    """
    directory = tmp_path / "site-packages" / "tzdata"
    _write_file(directory / "zones", _TZDATA_TEXT)

    return directory


@pytest.fixture
def mock_package_files(
    skill_directory: Path,
    tzdata_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Mock:
    """Replaces `_package_files` with a mock that knows the two fake packages.

    Args:
        skill_directory: The directory of the fake `bridge_skill` package.
        tzdata_directory: The directory of the fake `tzdata` package.
        monkeypatch: The fixture that installs the mock.

    Returns:
        The mock. Called with either directory, it returns the file of that package
        mapped to its path inside the zip.
    """
    skill_module = skill_directory / "lambda_function.py"

    mock = Mock(
        side_effect={
            skill_directory: {skill_module: "bridge_skill/lambda_function.py"},
            tzdata_directory: {tzdata_directory / "zones": "tzdata/zones"},
        }.__getitem__,
    )
    monkeypatch.setattr(f"{_DEPLOYMENT_ZIP_MODULE}._package_files", mock)

    return mock


@pytest.fixture
def mock_find_tzdata_directory(
    tzdata_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Mock:
    """Replaces `_find_tzdata_directory` with a mock returning the fake package.

    Args:
        tzdata_directory: The directory of the fake `tzdata` package.
        monkeypatch: The fixture that installs the mock.

    Returns:
        The mock.
    """
    mock = Mock(return_value=tzdata_directory)
    monkeypatch.setattr(f"{_DEPLOYMENT_ZIP_MODULE}._find_tzdata_directory", mock)

    return mock


@patch(f"{_DEPLOYMENT_ZIP_MODULE}.find_spec")
class TestFindTzdataDirectory:
    def test_looks_for_the_tzdata_package(self, mock_find_spec):
        _find_tzdata_directory()

        mock_find_spec.assert_called_once_with("tzdata")

    def test_missing_package_raises_module_not_found_error(self, mock_find_spec):
        mock_find_spec.return_value = None

        with pytest.raises(ModuleNotFoundError):
            _find_tzdata_directory()

    def test_package_without_an_origin_raises_module_not_found_error(
        self,
        mock_find_spec,
    ):
        mock_find_spec.return_value.origin = None

        with pytest.raises(ModuleNotFoundError):
            _find_tzdata_directory()

    def test_returns_the_directory_holding_the_package_init(self, mock_find_spec):
        package_directory = Path("site-packages") / "tzdata"

        mock_find_spec.return_value.origin = str(package_directory / "__init__.py")

        result = _find_tzdata_directory()

        assert result == package_directory


class TestPackageFiles:
    def test_directories_are_left_out(self, tmp_path):
        package_directory = tmp_path / "package"
        (package_directory / "empty").mkdir(parents=True)

        result = _package_files(package_directory)

        assert result == {}

    def test_cached_bytecode_is_left_out(self, tmp_path):
        package_directory = tmp_path / "package"
        _write_file(package_directory / "__pycache__" / "module.pyc", "bytecode")
        _write_file(package_directory / "sub" / "__pycache__" / "data.pyc", "bytecode")

        result = _package_files(package_directory)

        assert result == {}

    def test_maps_each_file_to_its_path_from_the_package_name(self, tmp_path):
        package_directory = tmp_path / "package"
        top_level_file = package_directory / "module.py"
        nested_file = package_directory / "sub" / "data.txt"
        _write_file(top_level_file, "module")
        _write_file(nested_file, "data")

        result = _package_files(package_directory)

        assert result == {
            top_level_file: "package/module.py",
            nested_file: "package/sub/data.txt",
        }


@pytest.mark.usefixtures(
    "repository_root",
    "mock_package_files",
    "mock_find_tzdata_directory",
)
class TestBuildDeploymentZip:
    def test_finds_the_tzdata_directory(self, tmp_path, mock_find_tzdata_directory):
        build_deployment_zip(tmp_path / "skill.zip")

        mock_find_tzdata_directory.assert_called_once_with()

    def test_packages_the_skill_and_tzdata_directories(
        self,
        tmp_path,
        skill_directory,
        tzdata_directory,
        mock_package_files,
    ):
        build_deployment_zip(tmp_path / "skill.zip")

        mock_package_files.assert_any_call(skill_directory)
        mock_package_files.assert_any_call(tzdata_directory)

    def test_leaves_out_shared_files_that_are_not_python(self, tmp_path):
        destination = tmp_path / "skill.zip"

        build_deployment_zip(destination)

        with ZipFile(destination) as archive:
            assert "notes.txt" not in archive.namelist()

    def test_zips_the_skill_package(self, tmp_path):
        destination = tmp_path / "skill.zip"

        build_deployment_zip(destination)

        with ZipFile(destination) as archive:
            result = archive.read("bridge_skill/lambda_function.py")

        assert result == _SKILL_MODULE_TEXT.encode()

    def test_zips_tzdata(self, tmp_path):
        destination = tmp_path / "skill.zip"

        build_deployment_zip(destination)

        with ZipFile(destination) as archive:
            assert archive.read("tzdata/zones") == _TZDATA_TEXT.encode()

    def test_makes_every_file_readable_by_everyone(self, tmp_path):
        destination = tmp_path / "skill.zip"

        build_deployment_zip(destination)

        with ZipFile(destination) as archive:
            permissions = {info.external_attr >> 16 for info in archive.infolist()}
        assert permissions == {_FILE_PERMISSIONS}

    def test_compresses_every_file(self, tmp_path):
        destination = tmp_path / "skill.zip"

        build_deployment_zip(destination)

        with ZipFile(destination) as archive:
            compression = {info.compress_type for info in archive.infolist()}
        assert compression == {ZIP_DEFLATED}

    def test_creates_the_missing_directories_of_the_destination(self, tmp_path):
        destination = tmp_path / "build" / "nested" / "skill.zip"

        build_deployment_zip(destination)

        assert destination.is_file()

    def test_replaces_a_zip_already_at_the_destination(self, tmp_path):
        destination = tmp_path / "skill.zip"
        with ZipFile(destination, "w") as stale_archive:
            stale_archive.writestr("stale.txt", "old")

        build_deployment_zip(destination)

        with ZipFile(destination) as archive:
            assert "stale.txt" not in archive.namelist()

    def test_zips_the_shared_python_modules_at_the_top_level(self, tmp_path):
        destination = tmp_path / "skill.zip"

        build_deployment_zip(destination)

        with ZipFile(destination) as archive:
            assert archive.read("bridge_closure.py") == _SHARED_MODULE_TEXT.encode()


@patch(f"{_DEPLOYMENT_ZIP_MODULE}.build_deployment_zip")
class TestMain:
    def test_builds_the_zip_at_the_default_destination(
        self,
        mock_build_deployment_zip,
    ):
        main()

        mock_build_deployment_zip.assert_called_once_with(_DEFAULT_DESTINATION)

    def test_prints_where_the_zip_was_written(
        self,
        mock_build_deployment_zip,
        capsys,
    ):
        main()

        assert f"Wrote {_DEFAULT_DESTINATION}" in capsys.readouterr().out
