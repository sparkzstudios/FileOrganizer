# FileOrganizer

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)

**FileOrganizer** is a fast, safe, zero-dependency command-line tool that
recursively scans a directory and automatically sorts every file it finds
into clean, categorized folders — Images, Videos, Audio, Documents,
Archives, Programming, Adobe, 3D, CAD, and more — based on file extension.

Point it at a messy `Downloads` folder, a photographer's dumping ground of
memory-card imports, or years of accumulated project files, and get back a
tidy, organized directory tree in seconds.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Command Line Reference](#command-line-reference)
- [Examples](#examples)
- [Folder Tree (Before / After)](#folder-tree-before--after)
- [Supported Categories](#supported-categories)
- [Duplicate File Handling](#duplicate-file-handling)
- [Screenshots](#screenshots)
- [FAQ](#faq)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [Version History](#version-history)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **Zero dependencies** — pure Python standard library, nothing to `pip install`.
- **250+ recognized file extensions** across 19 categories.
- **Recursive scanning** of the entire directory tree.
- **Move or copy** modes — keep your originals safe with `--copy`.
- **Dry-run mode** — preview exactly what would happen before touching a single file.
- **Safe duplicate handling** — `photo.jpg` → `photo (1).jpg` → `photo (2).jpg`, no overwrites, ever.
- **Optional folder-structure preservation** inside each category.
- **Optional empty-folder cleanup** after organizing.
- **Live progress bar** with zero external dependencies.
- **Detailed logging** to `organizer.log` plus an end-of-run summary report.
- **Graceful Ctrl+C handling** — stop anytime without corrupting anything.
- **Robust error handling** — permission errors, broken symlinks, unicode
  filenames, and overly long paths are all handled without crashing.
- **Skips hidden files, system files (Thumbs.db, .DS_Store, etc.), and
  symbolic links** automatically.
- **Cross-platform** — tested on Windows, macOS, and Linux.

---

## Installation

FileOrganizer requires **Python 3.11 or newer** and has **no external
dependencies**.

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/FileOrganizer.git
cd FileOrganizer

# 2. (Optional) confirm there is nothing to install
cat requirements.txt

# 3. Run it directly — no build step required
python organize_files.py --help
```

---

## Usage

The most basic invocation organizes the current directory in place:

```bash
python organize_files.py
```

Organize a specific folder:

```bash
python organize_files.py --source "/path/to/messy/folder"
```

**Always preview first with `--dry-run` before organizing anything important:**

```bash
python organize_files.py --source "~/Downloads" --dry-run --verbose
```

---

## Configuration

Every default lives in the `CONFIG` section at the top of `organize_files.py`
and can be edited directly, or overridden per-run with command-line flags
(flags always win). Key options:

| Variable                     | Default        | Description                                              |
|-------------------------------|----------------|-----------------------------------------------------------|
| `BASE_DIRECTORY`              | `.`            | Directory to scan.                                        |
| `OUTPUT_FOLDER_NAME`          | `Organized`    | Name of the generated top-level output folder.             |
| `MOVE_FILES`                  | `True`         | Move files into place.                                     |
| `COPY_FILES`                  | `False`        | Copy instead of move (overrides `MOVE_FILES`).             |
| `DELETE_EMPTY_FOLDERS`        | `False`        | Remove directories left empty after organizing.             |
| `PRESERVE_FOLDER_STRUCTURE`   | `False`        | Keep relative sub-folder layout inside each category.       |
| `SHOW_PROGRESS`                | `True`         | Show a live progress bar.                                   |
| `SHOW_SUMMARY`                 | `True`         | Show the end-of-run summary report.                          |
| `ENABLE_LOGGING`               | `True`         | Write a run log to `LOG_FILE`.                                |
| `LOG_FILE`                     | `organizer.log`| Path to the log file.                                          |
| `SKIP_HIDDEN_FILES`            | `True`         | Skip dotfiles / OS-hidden files.                                |
| `SKIP_SYSTEM_FILES`            | `True`         | Skip Thumbs.db, .DS_Store, etc.                                  |
| `CASE_INSENSITIVE`             | `True`         | Treat `.JPG` and `.jpg` the same.                                 |
| `DRY_RUN`                      | `False`        | Preview only, no filesystem changes.                                |
| `MAX_FILENAME_LENGTH`          | `150`          | Truncate very long filenames safely (extension preserved).           |
| `VERBOSE`                       | `False`        | Print per-file diagnostic detail.                                      |

---

## Command Line Reference

| Flag                     | Description                                                       |
|---------------------------|---------------------------------------------------------------------|
| `--source`, `-s PATH`     | Directory to organize.                                              |
| `--output`, `-o NAME`     | Name of the output folder.                                          |
| `--copy`                  | Copy files instead of moving them.                                  |
| `--move`                  | Move files (default). Overrides `--copy` if both are passed.        |
| `--dry-run`               | Preview only — make no changes.                                      |
| `--summary`               | Force-show the summary report.                                        |
| `--no-summary`            | Suppress the summary report.                                           |
| `--verbose`, `-v`         | Print detailed per-file diagnostics.                                    |
| `--delete-empty`          | Delete folders left empty after organizing.                              |
| `--preserve-structure`    | Preserve relative sub-folder structure inside categories.                 |
| `--no-progress`           | Disable the live progress bar.                                              |
| `--no-log`                | Disable writing to the log file.                                              |
| `--version`               | Print the version number and exit.                                              |
| `--help`, `-h`            | Show the full help message.                                                      |

---

## Examples

**Preview a Downloads cleanup without changing anything:**
```bash
python organize_files.py --source ~/Downloads --dry-run --verbose
```

**Copy (not move) photos from an SD card import into an organized archive, keeping originals:**
```bash
python organize_files.py --source /Volumes/SDCARD --output Sorted --copy
```

**Organize a project folder while keeping each category's internal folder layout:**
```bash
python organize_files.py --source ./ProjectFiles --preserve-structure
```

**Fully clean up a directory, removing any folders left empty afterward:**
```bash
python organize_files.py --source D:\OldBackup --delete-empty --summary
```

---

## Folder Tree (Before / After)

**Before:**
```
Downloads/
├── invoice.pdf
├── vacation.jpg
├── vacation2.jpg
├── mixtape.mp3
├── project.zip
├── script.py
└── notes/
    └── meeting.docx
```

**After (`python organize_files.py --source Downloads`):**
```
Downloads/
└── Organized/
    ├── Documents/
    │   ├── invoice.pdf
    │   └── meeting.docx
    ├── Images/
    │   ├── vacation.jpg
    │   └── vacation2.jpg
    ├── Audio/
    │   └── mixtape.mp3
    ├── Archives/
    │   └── project.zip
    └── Programming/
        └── script.py
```

---

## Supported Categories

Images · Videos · Audio · Documents · Archives · Fonts · Executables ·
Programming · Adobe · 3D · CAD · Disk Images · Virtual Machines · eBooks ·
Torrents · Databases · Scripts · Configuration Files · System Files ·
Unknown Files (fallback)

FileOrganizer ships with **250+ recognized extensions** spanning these
categories, including camera RAW formats (`.cr2`, `.nef`, `.arw`, `.dng`,
`.raf`...), Adobe native formats (`.psd`, `.ai`, `.indd`, `.prproj`,
`.aep`...), 3D/CAD formats (`.blend`, `.fbx`, `.obj`, `.dwg`, `.step`...),
virtual machine images (`.vmdk`, `.vhd`, `.ova`...), and dozens of
programming-language source files.

Anything not recognized is placed safely in `Unknown Files` rather than
being skipped or discarded.

---

## Duplicate File Handling

FileOrganizer **never overwrites an existing file.** If the destination
already contains a file with the same name, an incrementing suffix is
appended automatically, with no upper limit on the count:

```
photo.jpg
photo (1).jpg
photo (2).jpg
photo (3).jpg
...
```

---

## Screenshots

> _Add a screenshot of the live progress bar here: `docs/screenshot-progress.png`_

> _Add a screenshot of the end-of-run summary report here: `docs/screenshot-summary.png`_

> _Add a before/after folder screenshot here: `docs/screenshot-before-after.png`_

---

## FAQ

**Does this require any third-party libraries?**
No. FileOrganizer uses only the Python standard library.

**Will it overwrite my files?**
No. Duplicate filenames are automatically renamed; nothing is ever
silently overwritten.

**Can I undo an organizing run?**
Not automatically. Run with `--dry-run` first to preview the changes, and
consider `--copy` instead of the default move mode if you want to keep the
original layout intact.

**Does it touch hidden files or system files like Thumbs.db?**
No, both are skipped by default (`SKIP_HIDDEN_FILES` / `SKIP_SYSTEM_FILES`).

**Does it follow symbolic links?**
No, symlinks (and Windows junctions) are always skipped for safety.

**What happens if I run it twice in a row?**
FileOrganizer automatically skips its own output folder, so a second run
simply finds nothing new to organize.

**Can I stop it partway through?**
Yes — press `Ctrl+C` at any time. Whatever has already been organized
stays organized; nothing is left half-written.

---

## Troubleshooting

| Symptom                                   | Likely Cause / Fix                                                        |
|--------------------------------------------|------------------------------------------------------------------------------|
| `[ERROR] Source directory does not exist`  | Double-check the `--source` path (use quotes if it contains spaces).          |
| `PermissionError` logged for some files     | The account running the script lacks permission for that file — it is skipped, not fatal. |
| Files are not landing where expected        | Check `Unknown Files` — the extension may not be in `CATEGORY_EXTENSIONS`.     |
| Very long filenames                          | These are safely truncated per `MAX_FILENAME_LENGTH`; adjust if needed.          |
| Nothing happens on a second run              | Expected — files already organized live under `Organized/` and are skipped.       |

---

## Roadmap

- [ ] Optional JSON/YAML external configuration file support.
- [ ] Undo/rollback command using the run log.
- [ ] Rule-based custom categorization (regex / glob rules).
- [ ] Parallelized scanning for very large network drives.
- [ ] Optional GUI front-end.

---

## Version History

See [CHANGELOG.md](CHANGELOG.md) for the full history.

- **1.0.0** — Initial public release.

---

## Contributing

Contributions are welcome!

1. Fork the repository and create a feature branch.
2. Follow the existing code style (PEP 8, full type hints, docstrings on
   every function).
3. Add or update tests/examples for any behavioral change.
4. Open a pull request describing the change and its motivation.

Please open an issue first for large feature proposals so the design can
be discussed before implementation.

---

## License

Released under the PolyForm Noncommercial License 1.0.0 — free for personal, educational, research, and other noncommercial use. Commercial use requires a separate license from the copyright holder.
