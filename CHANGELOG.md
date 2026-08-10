# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-08-10

### Added
- Initial public release of FileOrganizer.
- Recursive directory scanning with automatic pruning of the output folder,
  hidden directories, and symbolic links.
- Extension-based classification engine covering 250+ extensions across
  19 categories (Images, Videos, Audio, Documents, Archives, Fonts,
  Executables, Programming, Adobe, 3D, CAD, Disk Images, Virtual Machines,
  eBooks, Torrents, Databases, Scripts, Configuration Files, System Files,
  and an Unknown Files fallback).
- Move mode and copy mode (`--move` / `--copy`).
- Dry-run mode (`--dry-run`) for safe previewing.
- Safe, unlimited duplicate-filename resolution (`file (1).ext`, `file (2).ext`, ...).
- Optional preservation of relative folder structure inside category folders
  (`--preserve-structure`).
- Optional empty-folder cleanup after organizing (`--delete-empty`).
- Dependency-free live progress bar.
- File-based logging (`organizer.log`) plus console logging.
- End-of-run summary report with per-category counts, skipped/error counts,
  and elapsed time.
- Graceful `Ctrl+C` handling with a valid partial summary on interruption.
- Robust error handling for permission errors, missing files, unicode
  filename issues, and general OS errors — no single bad file can crash a run.
- Automatic skipping of hidden files, common OS/system artifact files
  (Thumbs.db, .DS_Store, desktop.ini, etc.), and symbolic links/junctions.
- Filename sanitization and safe truncation for cross-platform compatibility,
  including long-path safety on Windows.
- Full command-line interface built on `argparse`.
- Complete project scaffold: README, MIT LICENSE, CHANGELOG, `.gitignore`,
  and an empty `requirements.txt` (no external dependencies).
