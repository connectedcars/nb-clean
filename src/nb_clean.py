"""Clean Jupyter notebooks of execution counts, metadata (and output if run with --no-output)."""

import argparse
import pathlib
import subprocess
import sys

import nbformat

VERSION = "1.3.0"
ATTRIBUTE = "*.ipynb filter=nb-clean"


def error(message: str, code: int) -> None:
    """Print error message to stderr and exit with code.

    Parameters
    ----------
    message : str
        Error message, printed to stderr.
    code : int
        Return code.

    """
    print(f"nb-clean: error: {message}", file=sys.stderr)
    sys.exit(code)


def git(*args: str) -> str:
    """Call a Git subcommand.

    Parameters
    ----------
    *args : str
        Git subcommand and arguments.

    Returns
    -------
    str
        stdout from Git.

    Examples
    --------
    >>> git('rev-parse', '--git-dir')
    .git

    """
    process = subprocess.run(
        ["git"] + list(args), stderr=subprocess.PIPE, stdout=subprocess.PIPE
    )

    if process.returncode == 128:
        error("not in a Git repository", 64)

    if process.returncode:
        error(process.stderr, process.returncode)

    stdout: str = process.stdout.decode().strip()
    return stdout


def attributes_path() -> pathlib.Path:
    """Get the attributes file path for the current Git repository.

    Returns
    -------
    pathlib.Path
        Path to the Git attributes file.

    Examples
    --------
    >>> attributes_path()
    PosixPath('.git/info/attributes')

    """
    git_dir = git("rev-parse", "--git-dir")
    return pathlib.Path(git_dir) / "info" / "attributes"


def print_version(args: argparse.Namespace) -> None:
    """Print the version number.

    Parameters
    ----------
    args : argparse.Namespace
        Unused.

    """
    del args  # Unused.
    print(f"nb-clean {VERSION}")


def configure_git(args: argparse.Namespace) -> None:
    """Configure Git repository to use nb-clean filter.

    Parameters
    ----------
    args : argparse.Namespace
        Arguments parsed from the command line

    """
    cl_input = args.input

    git("config", "filter.nb-clean.clean", "nb-clean clean")

    attributes = attributes_path()

    if attributes.is_file() and ATTRIBUTE in attributes.read_text():
        return

    with attributes.open("a") as file:
        file.write(f"\n{ATTRIBUTE}\n")


def unconfigure_git(args: argparse.Namespace) -> None:
    """Remove nb-clean filter from the Git repository.

    Parameters
    ----------
    args : argparse.Namespace
        Unused.

    """
    del args  # Unused.

    attributes = attributes_path()

    if attributes.is_file():
        original_contents = attributes.read_text().split("\n")
        revised_contents = [
            line for line in original_contents if line != ATTRIBUTE
        ]
        attributes.write_text("\n".join(revised_contents))

    git("config", "--remove-section", "filter.nb-clean")


def clean(args: argparse.Namespace) -> None:
    """Clean notebook of execution counts, metadata, and output.

    Parameters
    ----------
    args : argparse.Namespace
        Arguments parsed from the command line.

    """
    notebook = nbformat.read(args.input, as_version=nbformat.NO_CONVERT)

    for cell in notebook.cells:
        cell["metadata"] = {}
        if cell["cell_type"] == "code":
            cell["execution_count"] = None
            cell["outputs"] = []

    nbformat.write(notebook, args.output)


def main() -> None:
    """Parse command line arguments and call corresponding function."""
    parser = argparse.ArgumentParser(allow_abbrev=False, description=__doc__)
    subparsers = parser.add_subparsers(dest="subcommand")
    subparsers.required = True

    version_parser = subparsers.add_parser(
        "version", help="print version number"
    )
    version_parser.set_defaults(func=print_version)

    configure_parser = subparsers.add_parser(
        "configure-git",
        help="configure Git filter to clean notebooks before staging",
    )
    configure_parser.set_defaults(func=configure_git)

    unconfigure_parser = subparsers.add_parser(
        "unconfigure-git",
        help="remove Git filter that cleans notebooks before staging",
    )
    unconfigure_parser.set_defaults(func=unconfigure_git)

    clean_parser = subparsers.add_parser(
        "clean",
        help="clean notebook of cell execution counts, metadata, and outputs",
    )
    clean_parser.add_argument(
        "-i",
        "--in",
        nargs="?",
        type=argparse.FileType("r"),
        default=sys.stdin,
        help="input file",
    )
    clean_parser.add_argument(
        "-o",
        "--out",
        nargs="?",
        type=argparse.FileType("w"),
        default=sys.stdout,
        help="output file",
    )
    clean_parser.add_argument(
        "--no-output",
        default=False,
        help="remove outputs from notebook",
    )
    clean_parser.set_defaults(func=clean)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
