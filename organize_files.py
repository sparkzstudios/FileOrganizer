#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 FileOrganizer - A Robust, Production-Grade Recursive File Organizer
================================================================================

FileOrganizer scans a directory tree (recursively, by default) and sorts
every file it finds into category folders based on file extension (e.g.
Images, Videos, Audio, Documents, Archives, Programming, Adobe, 3D, CAD,
Databases, Fonts, Executables, and more).

It is designed to be:
    * Safe:          Dry-run mode, duplicate-safe renaming, never overwrites.
    * Fast:          Single-pass scanning using pathlib, no repeated stat()
                      calls, O(1) category lookups via a precomputed
                      extension-to-category dictionary.
    * Robust:         Handles permission errors, broken symlinks, unicode
                      filenames, extremely long paths, and Ctrl+C interrupts
                      gracefully without losing progress information.
    * Configurable:   Every behavior can be tuned either via the CONFIG
                      section at the top of this file or via command-line
                      flags (which always take precedence over CONFIG).
    * Transparent:    Optional logging to a file, a live progress indicator,
                      and a clean end-of-run summary report.

--------------------------------------------------------------------------------
USAGE
--------------------------------------------------------------------------------
    python organize_files.py --source "/path/to/messy/folder"
    python organize_files.py --source "." --dry-run --verbose
    python organize_files.py --source "D:\\Downloads" --copy --summary

Run `python organize_files.py --help` for the full list of options.

--------------------------------------------------------------------------------
AUTHOR / LICENSE
--------------------------------------------------------------------------------
    Project : FileOrganizer
    Version : 1.0.0
    License : MIT (see LICENSE file)

    Standard-library only. No third-party dependencies required.
================================================================================
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import stat
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set, Tuple


# ==============================================================================
# SECTION 1: CONFIGURATION
# ==============================================================================
# Everything below can be overridden at runtime by command-line arguments.
# These defaults are only used when the corresponding CLI flag is not given.
# Edit these values directly if you want to "bake in" your preferred defaults.
# ------------------------------------------------------------------------------

#: The directory that will be scanned and organized.
#: "." means "the current working directory" when the script is executed.
BASE_DIRECTORY: str = "."

#: Name of the top-level folder (created inside BASE_DIRECTORY) that will
#: hold all of the category subfolders (Images/, Videos/, Documents/, ...).
OUTPUT_FOLDER_NAME: str = "Organized"

#: If True, files are physically moved into their category folder.
#: This is the default behavior and is mutually exclusive with COPY_FILES.
MOVE_FILES: bool = True

#: If True, files are copied (original left untouched) instead of moved.
#: Setting this to True automatically implies MOVE_FILES = False.
COPY_FILES: bool = False

#: If True, any directory left completely empty after organizing
#: (because all of its files were moved out) will be deleted.
DELETE_EMPTY_FOLDERS: bool = False

#: If True, the relative sub-folder structure of the source tree is
#: preserved *inside* each category folder, e.g.:
#'      Organized/Images/Vacation2023/beach.jpg
#: instead of flattening everything directly into the category folder:
#'      Organized/Images/beach.jpg
PRESERVE_FOLDER_STRUCTURE: bool = False

#: If True, a lightweight, dependency-free progress indicator is printed
#: to stdout while files are being processed.
SHOW_PROGRESS: bool = True

#: If True, a formatted summary table is printed once organizing finishes.
SHOW_SUMMARY: bool = True

#: If True, all operations (start, finish, moves, skips, errors) are
#: written to LOG_FILE in addition to (optionally) stdout.
ENABLE_LOGGING: bool = True

#: Path (relative or absolute) to the log file used when ENABLE_LOGGING
#: is True.
LOG_FILE: str = "organizer.log"

#: If True, files/directories whose names begin with "." (Unix-style
#: hidden files) are skipped entirely and never touched.
SKIP_HIDDEN_FILES: bool = True

#: If True, well-known operating-system/metadata files and folders
#: (Thumbs.db, desktop.ini, .DS_Store, System Volume Information, etc.)
#: are skipped automatically.
SKIP_SYSTEM_FILES: bool = True

#: If True, extension matching ignores case (".JPG" is treated the same
#: as ".jpg"). Strongly recommended to leave this True.
CASE_INSENSITIVE: bool = True

#: If True, no filesystem changes are made at all. FileOrganizer will
#: print/log exactly what *would* happen, which is invaluable for a
#: first run against an important directory.
DRY_RUN: bool = False

#: Maximum length (in characters) allowed for a single filename component
#: (not the whole path). Longer filenames are safely truncated (while
#: preserving the file extension) to avoid OS-level path errors, most
#: notably the historical MAX_PATH limitation on Windows.
MAX_FILENAME_LENGTH: int = 150

#: If True, extra diagnostic detail (every file examined, every decision
#: made) is printed to stdout / written to the log. If False, only
#: high-level progress and the final summary are shown.
VERBOSE: bool = False


# ==============================================================================
# SECTION 2: EXTENSION -> CATEGORY MAPPING
# ==============================================================================
# This is the heart of FileOrganizer's classification engine. Each category
# maps to a set of file extensions (without the leading dot, lowercase).
# The mapping intentionally covers 250+ extensions across 19 categories so
# that the vast majority of real-world files are recognized out of the box.
#
# NOTE: If the same extension appears to conceptually belong to more than
# one category (e.g. ".psd" is both an "Image" and an "Adobe" file), it is
# assigned to the single MOST SPECIFIC category to avoid ambiguity. Adobe
# native formats are grouped under "Adobe" rather than "Images", for example.
# ------------------------------------------------------------------------------

CATEGORY_EXTENSIONS: Dict[str, Set[str]] = {

    "Images": {
        "jpg", "jpeg", "jpe", "jfif", "png", "gif", "bmp", "webp", "heic",
        "heif", "avif", "tiff", "tif", "ico", "svg", "svgz", "raw", "cr2",
        "cr3", "nef", "arw", "dng", "rw2", "orf", "raf", "pef", "srw",
        "x3f", "erf", "kdc", "mrw", "nrw", "dcr", "bay", "3fr", "ppm",
        "pgm", "pbm", "pnm", "jp2", "j2k", "wbmp", "heics", "cur",
    },

    "Videos": {
        "mp4", "mkv", "avi", "mov", "m4v", "wmv", "webm", "flv", "mpeg",
        "mpg", "mpe", "3gp", "3g2", "ts", "mts", "m2ts", "vob", "ogv",
        "rmvb", "rm", "divx", "asf", "f4v", "m2v", "mxf", "swf", "yuv",
        "vp9",
    },

    "Audio": {
        "mp3", "wav", "wave", "aac", "ogg", "oga", "opus", "m4a", "flac",
        "alac", "aiff", "aif", "aifc", "ape", "wma", "mid", "midi",
        "amr", "au", "ra", "dts", "ac3", "caf", "pcm", "m4b", "m4p",
    },

    "Documents": {
        "pdf", "txt", "rtf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
        "csv", "tsv", "odt", "ods", "odp", "epub", "mobi", "azw", "azw3",
        "md", "markdown", "log", "wpd", "wps", "pages", "key", "numbers",
        "one", "onetoc2", "xps", "oxps", "vsd", "vsdx",
    },

    "Archives": {
        "zip", "rar", "7z", "tar", "gz", "tgz", "bz2", "tbz2", "xz", "txz",
        "cab", "z", "lz", "lzma", "lz4", "zst", "arj", "ace", "cpio", "rpm",
        "deb", "pkg", "sit", "sitx", "war", "jar", "ear",
    },

    "Fonts": {
        "ttf", "otf", "woff", "woff2", "eot", "fon", "fnt", "pfb", "pfm",
    },

    "Executables": {
        "exe", "msi", "apk", "appx", "appxbundle", "dll", "app", "bin",
        "run", "com", "gadget", "msix", "msp", "ipa", "xap", "jad",
    },

    "Programming": {
        "py", "pyw", "pyc", "pyo", "pyx", "ipynb", "java", "class", "jar",
        "cpp", "cxx", "cc", "c", "h", "hpp", "hxx", "cs", "go", "rs",
        "swift", "kt", "kts", "dart", "php", "phtml", "html", "htm",
        "css", "scss", "sass", "less", "js", "mjs", "cjs", "ts", "tsx",
        "jsx", "json", "jsonc", "yaml", "yml", "xml", "sql", "toml",
        "ini", "cfg", "conf", "bat", "cmd", "ps1", "sh", "bash", "zsh",
        "fish", "rb", "erb", "pl", "pm", "lua", "r", "rmd", "scala",
        "groovy", "vb", "vbs", "asm", "s", "m", "mm", "clj", "cljs",
        "elm", "ex", "exs", "erl", "hrl", "hs", "lhs", "jl", "nim",
        "zig", "sol", "tf", "tfvars", "makefile", "cmake", "gradle",
        "pom", "gemfile", "dockerfile", "proto", "graphql", "gql",
    },

    "Adobe": {
        "psd", "psb", "ai", "eps", "indd", "idml", "prproj", "aep",
        "aepx", "xd", "prel", "fla", "swf", "aif", "aet",
    },

    "3D": {
        "blend", "blend1", "fbx", "obj", "stl", "dae", "glb", "gltf",
        "3ds", "max", "c4d", "ma", "mb", "usd", "usda", "usdc", "ply",
        "x3d", "lwo", "lws",
    },

    "CAD": {
        "dwg", "dxf", "step", "stp", "iges", "igs", "sldprt", "sldasm",
        "catpart", "catproduct", "prt", "ipt", "iam", "skp",
    },

    "Disk Images": {
        "iso", "img", "dmg", "toast", "vcd", "nrg", "mdf", "mds", "cue",
        "bin", "daa",
    },

    "Virtual Machines": {
        "vmdk", "vhd", "vhdx", "ova", "ovf", "vdi", "vbox", "qcow2",
        "hdd", "vmx",
    },

    "eBooks": {
        "epub", "mobi", "azw", "azw3", "azw4", "fb2", "lit", "prc",
        "cbr", "cbz",
    },

    "Torrents": {
        "torrent",
    },

    "Databases": {
        "db", "sqlite", "sqlite3", "mdb", "accdb", "dbf", "frm", "myd",
        "myi", "ibd", "bak",
    },

    "Scripts": {
        "bat", "cmd", "ps1", "sh", "bash", "zsh", "fish", "vbs", "applescript",
        "scpt", "command",
    },

    "Configuration Files": {
        "ini", "cfg", "conf", "config", "env", "properties", "plist",
        "reg", "manifest", "lock",
    },

    "System Files": {
        "sys", "dll", "drv", "vxd", "efi", "nls", "cpl", "ocx",
    },
}

#: Fallback category for any extension not found above (or for files with
#: no extension at all).
UNKNOWN_CATEGORY: str = "Unknown Files"

#: Filenames that are always skipped when SKIP_SYSTEM_FILES is True,
#: regardless of extension. Matching is case-insensitive.
SYSTEM_FILENAMES: Set[str] = {
    "thumbs.db", "desktop.ini", ".ds_store", "ehthumbs.db", "icon\r",
    "$recycle.bin", "system volume information", ".directory",
    "ntuser.dat", "pagefile.sys", "hiberfil.sys", "swapfile.sys",
}

#: A stable, human-friendly display order for the summary report. Any
#: category not listed here (there shouldn't be any) is appended at the end.
SUMMARY_DISPLAY_ORDER: List[str] = [
    "Images", "Videos", "Audio", "Documents", "Archives", "Fonts",
    "Executables", "Programming", "Adobe", "3D", "CAD", "Disk Images",
    "Virtual Machines", "eBooks", "Torrents", "Databases", "Scripts",
    "Configuration Files", "System Files", UNKNOWN_CATEGORY,
]


def _build_extension_lookup(mapping: Dict[str, Set[str]]) -> Dict[str, str]:
    """
    Flatten the CATEGORY_EXTENSIONS dictionary into a single, fast
    extension -> category lookup table.

    Building this once at import time (rather than scanning every category
    set for every single file) is what keeps classification at O(1) per
    file instead of O(categories) per file, which matters a great deal
    when organizing directories with hundreds of thousands of files.

    Args:
        mapping: The category -> set-of-extensions dictionary.

    Returns:
        A dictionary mapping each lowercase extension (without a dot) to
        the name of the category it belongs to. When an extension appears
        in more than one category in `mapping`, the category defined
        *first* wins (dict insertion order is preserved in Python 3.7+).
    """
    lookup: Dict[str, str] = {}
    for category, extensions in mapping.items():
        for ext in extensions:
            lookup.setdefault(ext.lower(), category)
    return lookup


#: Precomputed extension -> category lookup table (built once at import).
EXTENSION_LOOKUP: Dict[str, str] = _build_extension_lookup(CATEGORY_EXTENSIONS)


# ==============================================================================
# SECTION 3: DATA STRUCTURES
# ==============================================================================

@dataclass
class OrganizerConfig:
    """
    Immutable-in-spirit container for a single organizing run's settings.

    An instance of this class is built once (by merging CONFIG defaults
    with any CLI overrides) and then passed around to every function that
    needs to make a behavioral decision. Keeping configuration in one
    explicit object -- rather than reading module-level globals scattered
    throughout the code -- makes the program easier to test and reason
    about.
    """
    base_directory: Path
    output_folder_name: str = OUTPUT_FOLDER_NAME
    move_files: bool = MOVE_FILES
    copy_files: bool = COPY_FILES
    delete_empty_folders: bool = DELETE_EMPTY_FOLDERS
    preserve_folder_structure: bool = PRESERVE_FOLDER_STRUCTURE
    show_progress: bool = SHOW_PROGRESS
    show_summary: bool = SHOW_SUMMARY
    enable_logging: bool = ENABLE_LOGGING
    log_file: str = LOG_FILE
    skip_hidden_files: bool = SKIP_HIDDEN_FILES
    skip_system_files: bool = SKIP_SYSTEM_FILES
    case_insensitive: bool = CASE_INSENSITIVE
    dry_run: bool = DRY_RUN
    max_filename_length: int = MAX_FILENAME_LENGTH
    verbose: bool = VERBOSE

    def __post_init__(self) -> None:
        """Resolve conflicting flags into a single, unambiguous mode."""
        # --copy always wins over --move if both were somehow requested,
        # since copying is the strictly "safer" of the two operations.
        if self.copy_files:
            self.move_files = False

    @property
    def output_directory(self) -> Path:
        """Absolute path to the top-level folder that will hold results."""
        return self.base_directory / self.output_folder_name


@dataclass
class RunStatistics:
    """
    Accumulates counters for a single FileOrganizer run so that an accurate
    end-of-run summary can be printed regardless of how many files were
    processed or how many errors were encountered along the way.
    """
    per_category_counts: Dict[str, int] = field(default_factory=dict)
    skipped_count: int = 0
    error_count: int = 0
    total_files_seen: int = 0
    empty_folders_removed: int = 0
    start_time: float = field(default_factory=time.monotonic)
    end_time: Optional[float] = None

    def record_success(self, category: str) -> None:
        """Increment the counter for a category after a successful move/copy."""
        self.per_category_counts[category] = (
            self.per_category_counts.get(category, 0) + 1
        )

    def record_skip(self) -> None:
        """Increment the skipped-file counter."""
        self.skipped_count += 1

    def record_error(self) -> None:
        """Increment the error counter."""
        self.error_count += 1

    def finish(self) -> None:
        """Mark the run as complete and freeze the elapsed-time clock."""
        self.end_time = time.monotonic()

    @property
    def elapsed_seconds(self) -> float:
        """Total wall-clock time elapsed since the run began, in seconds."""
        end = self.end_time if self.end_time is not None else time.monotonic()
        return end - self.start_time

    @property
    def total_organized(self) -> int:
        """Total number of files successfully moved or copied."""
        return sum(self.per_category_counts.values())


# ==============================================================================
# SECTION 4: LOGGING SETUP
# ==============================================================================

def configure_logging(config: OrganizerConfig) -> logging.Logger:
    """
    Configure and return the module-level logger used throughout the run.

    When `config.enable_logging` is True, log records are written both to
    `config.log_file` (always, in append mode so history is preserved
    across runs) and to stdout. When logging is disabled, only a null
    handler is attached so that `logger.info(...)` calls elsewhere in the
    code remain safe no-ops rather than requiring guard checks everywhere.

    Args:
        config: The active OrganizerConfig for this run.

    Returns:
        A fully configured `logging.Logger` instance named "FileOrganizer".
    """
    logger = logging.getLogger("FileOrganizer")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()  # Avoid duplicate handlers on repeated calls.
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if config.enable_logging:
        try:
            file_handler = logging.FileHandler(
                config.log_file, mode="a", encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.DEBUG)
            logger.addHandler(file_handler)
        except OSError as exc:
            # If we can't open the log file (e.g. permissions), fall back to
            # console-only logging rather than crashing the whole program.
            print(f"[WARNING] Could not open log file '{config.log_file}': {exc}")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    console_handler.setLevel(logging.DEBUG if config.verbose else logging.INFO)
    logger.addHandler(console_handler)

    return logger


# ==============================================================================
# SECTION 5: CORE HELPER FUNCTIONS
# ==============================================================================

def get_category_for_file(file_path: Path, config: OrganizerConfig) -> str:
    """
    Determine which category a given file belongs to based on its
    extension.

    Args:
        file_path: The file whose category should be determined.
        config: The active OrganizerConfig (used for the
            `case_insensitive` setting).

    Returns:
        The category name (e.g. "Images", "Videos") the file's extension
        maps to, or `UNKNOWN_CATEGORY` if the extension is unrecognized
        or the file has no extension at all.
    """
    suffix = file_path.suffix  # Includes the leading dot, e.g. ".JPG".
    if not suffix:
        return UNKNOWN_CATEGORY

    extension = suffix.lstrip(".")
    if config.case_insensitive:
        extension = extension.lower()

    return EXTENSION_LOOKUP.get(extension, UNKNOWN_CATEGORY)


def is_hidden(path: Path) -> bool:
    """
    Determine whether a file or directory should be considered "hidden".

    On Unix-like systems this simply means the name starts with a dot.
    On Windows, we additionally check the FILE_ATTRIBUTE_HIDDEN flag so
    that files hidden purely through Windows Explorer attributes (without
    a leading dot in the name) are also correctly detected.

    Args:
        path: The path to check.

    Returns:
        True if the path should be treated as hidden, False otherwise.
    """
    if path.name.startswith("."):
        return True

    if os.name == "nt":
        try:
            attrs = os.stat(path).st_file_attributes  # type: ignore[attr-defined]
            return bool(attrs & stat.FILE_ATTRIBUTE_HIDDEN)
        except (AttributeError, OSError):
            # st_file_attributes is Windows-only; if unavailable, or the
            # stat call fails (e.g. broken symlink), fall through safely.
            return False

    return False


def is_system_file(path: Path) -> bool:
    """
    Determine whether a path refers to a well-known OS/metadata file or
    folder that should never be organized (Thumbs.db, .DS_Store, the
    Windows Recycle Bin, etc.).

    Args:
        path: The path to check.

    Returns:
        True if the path's name matches a known system artifact.
    """
    return path.name.lower() in SYSTEM_FILENAMES


def is_within_output_directory(path: Path, config: OrganizerConfig) -> bool:
    """
    Determine whether `path` lives inside the organizer's own output
    directory, which must always be skipped during scanning to prevent
    FileOrganizer from re-processing files it has already organized (which
    would otherwise cause infinite shuffling on repeated runs).

    Args:
        path: The path to check.
        config: The active OrganizerConfig.

    Returns:
        True if `path` is the output directory or is nested inside it.
    """
    try:
        path.relative_to(config.output_directory)
        return True
    except ValueError:
        return False


def sanitize_filename(filename: str, max_length: int) -> str:
    """
    Ensure a filename is safe to create on all major operating systems.

    This strips characters that are illegal on Windows (``<>:"/\\|?*`` and
    ASCII control characters), trims surrounding whitespace, and truncates
    the *stem* of the filename (never the extension) if the full name
    would otherwise exceed `max_length` characters -- which helps avoid
    hitting the legacy Windows MAX_PATH limit on deeply nested
    destinations.

    Args:
        filename: The original filename (name + extension, no directory).
        max_length: Maximum allowed length, in characters, for the
            filename component.

    Returns:
        A sanitized filename that is safe to use across platforms.
    """
    illegal_chars = '<>:"/\\|?*'
    control_chars = "".join(chr(i) for i in range(32))
    translation_table = {ord(c): "_" for c in illegal_chars + control_chars}
    cleaned = filename.translate(translation_table).strip().rstrip(".")

    if not cleaned:
        cleaned = "unnamed_file"

    if len(cleaned) <= max_length:
        return cleaned

    stem, dot, ext = cleaned.rpartition(".")
    if not dot:
        # No extension at all -- just hard-truncate the whole name.
        return cleaned[:max_length]

    # Reserve space for the extension (plus its dot) and truncate the stem.
    reserved = len(ext) + 1
    available = max(1, max_length - reserved)
    return f"{stem[:available]}.{ext}"


def resolve_duplicate_path(destination: Path) -> Path:
    """
    Given a desired destination path, return a path guaranteed not to
    collide with an existing file.

    If `destination` does not already exist, it is returned unchanged.
    Otherwise, this appends an incrementing " (n)" suffix to the filename
    -- immediately before the extension -- and keeps incrementing until an
    unused path is found, exactly matching common OS/Explorer conventions:

        photo.jpg -> photo (1).jpg -> photo (2).jpg -> photo (3).jpg -> ...

    There is no upper bound on the number of duplicates supported.

    Args:
        destination: The originally desired destination path.

    Returns:
        A `Path` that is guaranteed not to exist at the time of the check.
    """
    if not destination.exists():
        return destination

    parent = destination.parent
    stem = destination.stem
    suffix = destination.suffix  # Includes the leading dot, if any.

    counter = 1
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def format_elapsed_time(seconds: float) -> str:
    """
    Format a duration in seconds as an ``HH:MM:SS`` string, matching the
    style used in the end-of-run summary report.

    Args:
        seconds: Elapsed duration, in seconds.

    Returns:
        A zero-padded ``HH:MM:SS`` string.
    """
    total_seconds = int(round(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def print_progress(current: int, total: int, width: int = 40) -> None:
    """
    Render a lightweight, dependency-free progress bar to stdout.

    Uses a carriage return (``\\r``) to redraw the bar in place rather
    than printing a new line per file, so output stays readable even for
    directories containing hundreds of thousands of files.

    Args:
        current: Number of files processed so far.
        total: Total number of files to process (must be >= 1).
        width: Character width of the progress bar itself.
    """
    if total <= 0:
        return

    fraction = min(1.0, current / total)
    filled = int(width * fraction)
    bar = "#" * filled + "-" * (width - filled)
    percent = fraction * 100
    sys.stdout.write(f"\r[{bar}] {percent:6.2f}%  ({current}/{total})")
    sys.stdout.flush()

    if current >= total:
        sys.stdout.write("\n")
        sys.stdout.flush()


# ==============================================================================
# SECTION 6: DIRECTORY SCANNING
# ==============================================================================

def scan_files(
    base_directory: Path, config: OrganizerConfig, logger: logging.Logger
) -> List[Path]:
    """
    Recursively walk `base_directory` and return every regular file that
    should be considered for organizing.

    This performs all of the "should we even look at this file?" filtering
    up front (hidden files, system files, symlinks, the output directory
    itself) so that the main processing loop can stay focused purely on
    classification and moving/copying.

    Args:
        base_directory: The root directory to scan.
        config: The active OrganizerConfig.
        logger: Logger used to record skipped entries when verbose.

    Returns:
        A list of `Path` objects for every file that will be organized.
        The list is materialized (rather than left as a lazy generator) so
        that an accurate total file count is available up front for the
        progress bar and summary report.
    """
    discovered: List[Path] = []

    for root, dir_names, file_names in os.walk(base_directory, onerror=_log_walk_error):
        root_path = Path(root)

        # Prune directories we should never descend into, in-place, so
        # os.walk does not bother recursing into them at all. This is both
        # a correctness measure (skip our own output folder, skip hidden
        # directories) and a significant performance optimization on large
        # trees.
        pruned_dir_names = []
        for dir_name in dir_names:
            dir_path = root_path / dir_name

            if is_within_output_directory(dir_path, config):
                continue
            if config.skip_hidden_files and is_hidden(dir_path):
                continue
            if config.skip_system_files and is_system_file(dir_path):
                continue
            if dir_path.is_symlink():
                # Never follow symlinked directories -- avoids potential
                # infinite loops from circular symlinks and matches the
                # "skip symbolic links / junctions" requirement.
                continue

            pruned_dir_names.append(dir_name)

        dir_names[:] = pruned_dir_names

        for file_name in file_names:
            file_path = root_path / file_name

            if _resolves_to_log_file(file_path, config):
                # Never organize FileOrganizer's own log file out from
                # under itself -- doing so would relocate an actively
                # open file handle mid-run.
                continue
            if file_path.is_symlink():
                if config.verbose:
                    logger.debug("Skipping symbolic link: %s", file_path)
                continue
            if config.skip_hidden_files and is_hidden(file_path):
                if config.verbose:
                    logger.debug("Skipping hidden file: %s", file_path)
                continue
            if config.skip_system_files and is_system_file(file_path):
                if config.verbose:
                    logger.debug("Skipping system file: %s", file_path)
                continue

            discovered.append(file_path)

    return discovered


def _resolves_to_log_file(file_path: Path, config: OrganizerConfig) -> bool:
    """
    Determine whether `file_path` refers to the active log file so that
    scanning can exclude it, preventing FileOrganizer from relocating its
    own actively-open log while a run is still in progress.

    Args:
        file_path: The candidate file discovered during scanning.
        config: The active OrganizerConfig (used for `log_file`).

    Returns:
        True if `file_path` is the same file as `config.log_file`.
    """
    if not config.enable_logging:
        return False
    try:
        return file_path.resolve() == Path(config.log_file).resolve()
    except OSError:
        return False


def _log_walk_error(os_error: OSError) -> None:
    """
    Error callback passed to `os.walk` so that permission errors (or other
    OS-level failures) encountered while *listing* a directory are recorded
    rather than silently swallowed or allowed to crash the walk.

    Args:
        os_error: The exception raised by `os.walk` for a given directory.
    """
    logger = logging.getLogger("FileOrganizer")
    logger.warning("Could not access directory '%s': %s", os_error.filename, os_error)


# ==============================================================================
# SECTION 7: FILE PROCESSING (THE ORGANIZING ENGINE)
# ==============================================================================

def compute_destination_path(
    file_path: Path,
    category: str,
    base_directory: Path,
    config: OrganizerConfig,
) -> Path:
    """
    Compute the final destination path for a given source file, taking
    into account the configured category folder, optional preservation of
    the original relative folder structure, and filename sanitization.

    Args:
        file_path: The source file being organized.
        category: The category this file was classified into.
        base_directory: The root directory being scanned (used to compute
            the file's relative path when PRESERVE_FOLDER_STRUCTURE is on).
        config: The active OrganizerConfig.

    Returns:
        The (not-yet-deduplicated) destination `Path` for this file.
    """
    category_root = config.output_directory / category
    safe_name = sanitize_filename(file_path.name, config.max_filename_length)

    if config.preserve_folder_structure:
        try:
            relative_parent = file_path.parent.relative_to(base_directory)
        except ValueError:
            relative_parent = Path(".")
        destination_dir = category_root / relative_parent
    else:
        destination_dir = category_root

    return destination_dir / safe_name


def process_single_file(
    file_path: Path,
    base_directory: Path,
    config: OrganizerConfig,
    stats: RunStatistics,
    logger: logging.Logger,
) -> None:
    """
    Classify and organize (move or copy) a single file, fully handling
    every recoverable error condition so that one bad file never aborts
    an entire run.

    Args:
        file_path: The file to process.
        base_directory: The root directory being scanned.
        config: The active OrganizerConfig.
        stats: The RunStatistics object being accumulated for this run.
        logger: Logger used to record per-file outcomes.
    """
    try:
        category = get_category_for_file(file_path, config)
        destination = compute_destination_path(
            file_path, category, base_directory, config
        )
        destination = resolve_duplicate_path(destination)

        if config.verbose:
            action = "Would move" if config.dry_run else (
                "Copying" if config.copy_files else "Moving"
            )
            logger.debug("%s '%s' -> '%s'", action, file_path, destination)

        if config.dry_run:
            stats.record_success(category)
            return

        destination.parent.mkdir(parents=True, exist_ok=True)

        if config.copy_files:
            shutil.copy2(file_path, destination)
        else:
            shutil.move(str(file_path), str(destination))

        stats.record_success(category)

    except PermissionError as exc:
        stats.record_error()
        logger.error("Permission denied processing '%s': %s", file_path, exc)
    except FileNotFoundError as exc:
        stats.record_error()
        logger.error("File disappeared before it could be processed '%s': %s", file_path, exc)
    except UnicodeError as exc:
        stats.record_error()
        logger.error("Unicode/encoding error processing '%s': %s", file_path, exc)
    except OSError as exc:
        stats.record_error()
        logger.error("OS error processing '%s': %s", file_path, exc)
    except Exception as exc:  # noqa: BLE001 - final safety net, by design.
        # FileOrganizer must never crash mid-run because of a single
        # unexpected file. Log the full traceback for diagnosis and
        # continue on to the next file.
        stats.record_error()
        logger.error("Unexpected error processing '%s': %s", file_path, exc)
        logger.debug(traceback.format_exc())


def remove_empty_directories(base_directory: Path, config: OrganizerConfig,
                              stats: RunStatistics, logger: logging.Logger) -> None:
    """
    Walk `base_directory` bottom-up and remove any directory left
    completely empty as a result of organizing (files having been moved
    out of it). The output directory itself is always preserved.

    This function is a no-op unless `config.delete_empty_folders` is True,
    and it never removes non-empty directories or the output directory.

    Args:
        base_directory: The root directory that was scanned.
        config: The active OrganizerConfig.
        stats: The RunStatistics object to update with removal counts.
        logger: Logger used to record each removed directory.
    """
    if not config.delete_empty_folders:
        return

    # Bottom-up traversal (topdown=False) guarantees that a directory's
    # children have already been evaluated (and possibly removed) before
    # we check whether the directory itself is now empty.
    for root, dir_names, file_names in os.walk(base_directory, topdown=False):
        root_path = Path(root)

        if is_within_output_directory(root_path, config):
            continue
        if root_path == base_directory:
            continue

        try:
            is_empty = not any(root_path.iterdir())
        except OSError as exc:
            logger.warning("Could not inspect '%s' for emptiness: %s", root_path, exc)
            continue

        if is_empty:
            try:
                if not config.dry_run:
                    root_path.rmdir()
                stats.empty_folders_removed += 1
                if config.verbose:
                    logger.debug("Removed empty directory: %s", root_path)
            except OSError as exc:
                logger.warning("Could not remove empty directory '%s': %s", root_path, exc)


# ==============================================================================
# SECTION 8: SUMMARY REPORTING
# ==============================================================================

def build_summary_report(stats: RunStatistics) -> str:
    """
    Render the final RunStatistics into the human-readable summary block
    shown at the end of every run (and written to the log file).

    Args:
        stats: The completed RunStatistics for this run.

    Returns:
        A multi-line string ready to be printed or logged.
    """
    width = 40
    lines: List[str] = []
    lines.append("=" * width)
    lines.append("FILE ORGANIZER SUMMARY")
    lines.append("=" * width)

    ordered_categories = list(SUMMARY_DISPLAY_ORDER)
    for category in stats.per_category_counts:
        if category not in ordered_categories:
            ordered_categories.append(category)

    label_width = 16
    for category in ordered_categories:
        count = stats.per_category_counts.get(category, 0)
        if count == 0 and category not in stats.per_category_counts:
            continue
        dots = "." * max(1, label_width - len(category))
        lines.append(f"{category} {dots} {count}")

    lines.append(f"{'Skipped':<{label_width}} {'.' * 8} {stats.skipped_count}")
    lines.append(f"{'Errors':<{label_width}} {'.' * 9} {stats.error_count}")
    lines.append(f"{'Total Files':<{label_width}} {'.' * 4} {stats.total_files_seen}")
    lines.append(
        f"{'Elapsed Time':<{label_width}} {'.' * 3} {format_elapsed_time(stats.elapsed_seconds)}"
    )
    lines.append("=" * width)

    if stats.empty_folders_removed:
        lines.append(f"Empty folders removed: {stats.empty_folders_removed}")
        lines.append("=" * width)

    return "\n".join(lines)


# ==============================================================================
# SECTION 9: COMMAND-LINE INTERFACE
# ==============================================================================

def build_arg_parser() -> argparse.ArgumentParser:
    """
    Construct the `argparse.ArgumentParser` used to parse command-line
    arguments for FileOrganizer.

    Returns:
        A fully configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="organize_files.py",
        description=(
            "FileOrganizer - recursively scan a directory and sort files "
            "into category folders (Images, Videos, Documents, and more) "
            "based on their extensions."
        ),
        epilog=(
            "Examples:\n"
            "  python organize_files.py --source ~/Downloads\n"
            "  python organize_files.py --source . --dry-run --verbose\n"
            "  python organize_files.py --source D:\\Data --copy --summary\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--source", "-s", type=str, default=None,
        help=f"Directory to organize. Defaults to CONFIG value: '{BASE_DIRECTORY}'.",
    )
    parser.add_argument(
        "--output", "-o", type=str, default=None,
        help=f"Name of the output folder. Defaults to '{OUTPUT_FOLDER_NAME}'.",
    )
    parser.add_argument(
        "--copy", action="store_true",
        help="Copy files instead of moving them (originals are preserved).",
    )
    parser.add_argument(
        "--move", action="store_true",
        help="Move files (default behavior). Overrides --copy if both are given.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview what would happen without making any filesystem changes.",
    )
    parser.add_argument(
        "--summary", action="store_true",
        help="Force-display the end-of-run summary report (on by default).",
    )
    parser.add_argument(
        "--no-summary", action="store_true",
        help="Suppress the end-of-run summary report.",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print detailed per-file diagnostic information.",
    )
    parser.add_argument(
        "--delete-empty", action="store_true",
        help="Delete directories left empty after files are moved out.",
    )
    parser.add_argument(
        "--preserve-structure", action="store_true",
        help="Preserve the original relative folder structure inside each "
             "category folder instead of flattening files.",
    )
    parser.add_argument(
        "--no-progress", action="store_true",
        help="Disable the live progress bar (useful for CI/non-TTY output).",
    )
    parser.add_argument(
        "--no-log", action="store_true",
        help="Disable writing to the log file.",
    )
    parser.add_argument(
        "--version", action="version", version="FileOrganizer 1.0.0",
    )

    return parser


def build_config_from_args(args: argparse.Namespace) -> OrganizerConfig:
    """
    Merge parsed command-line arguments with the module-level CONFIG
    defaults to produce a final `OrganizerConfig` for this run.

    Command-line flags always take precedence over the CONFIG section
    defaults defined at the top of this file.

    Args:
        args: The parsed `argparse.Namespace`.

    Returns:
        A fully populated `OrganizerConfig` instance.
    """
    source = args.source if args.source is not None else BASE_DIRECTORY
    base_directory = Path(source).expanduser().resolve()

    move_files = MOVE_FILES
    copy_files = COPY_FILES
    if args.copy:
        copy_files = True
        move_files = False
    if args.move:
        move_files = True
        copy_files = False

    show_summary = SHOW_SUMMARY
    if args.summary:
        show_summary = True
    if args.no_summary:
        show_summary = False

    return OrganizerConfig(
        base_directory=base_directory,
        output_folder_name=args.output if args.output is not None else OUTPUT_FOLDER_NAME,
        move_files=move_files,
        copy_files=copy_files,
        delete_empty_folders=args.delete_empty or DELETE_EMPTY_FOLDERS,
        preserve_folder_structure=args.preserve_structure or PRESERVE_FOLDER_STRUCTURE,
        show_progress=not args.no_progress and SHOW_PROGRESS,
        show_summary=show_summary,
        enable_logging=not args.no_log and ENABLE_LOGGING,
        log_file=LOG_FILE,
        skip_hidden_files=SKIP_HIDDEN_FILES,
        skip_system_files=SKIP_SYSTEM_FILES,
        case_insensitive=CASE_INSENSITIVE,
        dry_run=args.dry_run or DRY_RUN,
        max_filename_length=MAX_FILENAME_LENGTH,
        verbose=args.verbose or VERBOSE,
    )


# ==============================================================================
# SECTION 10: VALIDATION
# ==============================================================================

def validate_config(config: OrganizerConfig) -> None:
    """
    Validate an `OrganizerConfig` before any filesystem changes are made,
    raising a clear, user-facing error for any invalid setup.

    Args:
        config: The OrganizerConfig to validate.

    Raises:
        SystemExit: If validation fails, with a helpful message printed
            to stderr describing exactly what is wrong.
    """
    if not config.base_directory.exists():
        sys.exit(f"[ERROR] Source directory does not exist: {config.base_directory}")

    if not config.base_directory.is_dir():
        sys.exit(f"[ERROR] Source path is not a directory: {config.base_directory}")

    if not os.access(config.base_directory, os.R_OK):
        sys.exit(f"[ERROR] No read permission for source directory: {config.base_directory}")

    if config.max_filename_length < 8:
        sys.exit("[ERROR] MAX_FILENAME_LENGTH must be at least 8 characters.")


# ==============================================================================
# SECTION 11: MAIN ORCHESTRATION
# ==============================================================================

def run_organizer(config: OrganizerConfig, logger: logging.Logger) -> RunStatistics:
    """
    Execute a full organizing run: scan, classify, move/copy, and
    optionally clean up empty directories, returning the accumulated
    statistics.

    This function contains the top-level control flow and is where
    KeyboardInterrupt (Ctrl+C) is caught so that a partial run still
    produces a valid, informative summary instead of an ugly traceback.

    Args:
        config: The active OrganizerConfig for this run.
        logger: The configured logger for this run.

    Returns:
        The `RunStatistics` object describing what happened during the run.
    """
    stats = RunStatistics()

    mode = "DRY RUN" if config.dry_run else ("COPY" if config.copy_files else "MOVE")
    logger.info("=" * 40)
    logger.info("FileOrganizer starting")
    logger.info("Source directory : %s", config.base_directory)
    logger.info("Output directory : %s", config.output_directory)
    logger.info("Mode             : %s", mode)
    logger.info("=" * 40)

    try:
        files = scan_files(config.base_directory, config, logger)
        stats.total_files_seen = len(files)
        logger.info("Discovered %d file(s) to process.", len(files))

        for index, file_path in enumerate(files, start=1):
            process_single_file(file_path, config.base_directory, config, stats, logger)

            if config.show_progress and not config.verbose:
                print_progress(index, len(files))

        remove_empty_directories(config.base_directory, config, stats, logger)

    except KeyboardInterrupt:
        # Graceful interruption: whatever has already been organized stays
        # organized (we never leave a file half-written), and the user
        # gets an accurate partial summary instead of a stack trace.
        logger.warning("Interrupted by user (Ctrl+C). Finishing up safely...")
        print("\n[INTERRUPTED] Stopping early — showing partial summary below.")

    finally:
        stats.finish()

    logger.info("FileOrganizer finished.")
    return stats


def main(argv: Optional[List[str]] = None) -> int:
    """
    Program entry point: parse arguments, validate configuration, run the
    organizer, and print the summary report.

    Args:
        argv: Optional list of command-line arguments (primarily for
            testing). Defaults to `sys.argv[1:]` when None.

    Returns:
        A process exit code: 0 on success, 1 if a fatal error occurred.
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        config = build_config_from_args(args)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Invalid configuration: {exc}", file=sys.stderr)
        return 1

    validate_config(config)
    logger = configure_logging(config)

    if config.dry_run:
        logger.info("Running in DRY RUN mode — no files will be changed.")

    stats = run_organizer(config, logger)

    if config.show_summary:
        report = build_summary_report(stats)
        print("\n" + report)
        logger.info("\n%s", report)

    return 0 if stats.error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
