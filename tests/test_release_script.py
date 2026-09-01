# Copyright 2018 Comcast Cable Communications Management, LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import shutil
import subprocess
from pathlib import Path


def create_fake_python3(bin_dir: Path, log_file: Path) -> None:
    """Create a fake python3 executable that handles version probes, import checks,
    and records -m build and -m twine invocations."""

    fake_python = bin_dir / "python3"
    fake_python.write_text(f'''#!/usr/bin/env bash
set -e

LOG_FILE="{log_file}"

# Log all invocations
echo "python3 $@" >> "$LOG_FILE"

# Handle version check
if [[ "$1" == "-c" ]] && [[ "$2" == *"sys.version_info"* ]]; then
    echo "3.11"
    exit 0
fi

# Handle import checks
if [[ "$1" == "-c" ]] && [[ "$2" == *"import "* ]]; then
    exit 0
fi

# Handle -m build - return failure for this test
if [[ "$1" == "-m" ]] && [[ "$2" == "build" ]]; then
    echo "ERROR: Build failed" >&2
    exit 1
fi

# Handle -m twine - should not be called in this test
if [[ "$1" == "-m" ]] && [[ "$2" == "twine" ]]; then
    echo "ERROR: twine should not be called after build failure" >&2
    exit 1
fi

# Default: unknown invocation
echo "ERROR: Unknown python3 invocation: $@" >&2
exit 1
''', encoding='utf-8')
    fake_python.chmod(0o755)


def create_fake_git(bin_dir: Path, log_file: Path, test_dir: Path) -> None:
    """Create a fake git executable that handles status, remote, and push commands."""

    fake_git = bin_dir / "git"
    fake_git.write_text(f'''#!/usr/bin/env bash

LOG_FILE="{log_file}"

# Log all invocations
echo "git $@" >> "$LOG_FILE"

case "$1" in
    status)
        if [[ "$2" == "--porcelain" ]]; then
            # Return empty output (clean working directory)
            exit 0
        elif [[ "$2" == "--short" ]]; then
            exit 0
        fi
        ;;
    remote)
        if [[ "$2" == "get-url" ]]; then
            # Pretend the remote exists
            echo "https://github.com/vinyldns/vinyldns-python.git"
            exit 0
        elif [[ "$2" == "-v" ]]; then
            echo "origin\thttps://github.com/vinyldns/vinyldns-python.git (fetch)"
            echo "origin\thttps://github.com/vinyldns/vinyldns-python.git (push)"
            exit 0
        fi
        ;;
    symbolic-ref)
        if [[ "$2" == "--short" ]] && [[ "$3" == "HEAD" ]]; then
            echo "main"
            exit 0
        fi
        ;;
    describe)
        if [[ "$2" == "--exact-match" ]] && [[ "$3" == "--tags" ]]; then
            echo "v0.9.11"
            exit 0
        fi
        ;;
    push)
        # Forbidden operation - fail immediately
        echo "ERROR: git push should not be called in this test" >&2
        exit 1
        ;;
esac

# Default: unknown invocation
echo "ERROR: Unknown git invocation: $@" >&2
exit 1
''', encoding='utf-8')
    fake_git.chmod(0o755)


def create_fake_gpg(bin_dir: Path, log_file: Path) -> None:
    """Create a fake gpg executable that handles key checks and signing."""

    fake_gpg = bin_dir / "gpg"
    fake_gpg.write_text(f'''#!/usr/bin/env bash

LOG_FILE="{log_file}"

# Log all invocations
echo "gpg $@" >> "$LOG_FILE"

# Handle --list-secret-keys (preflight check)
if [[ "$1" == "--list-secret-keys" ]]; then
    # Just succeed - key exists
    exit 0
fi

# Handle signing with --detach-sign
if [[ "$2" == "-u" ]] && [[ "$4" == "--detach-sign" ]]; then
    # Forbidden operation - fail immediately
    echo "ERROR: gpg --detach-sign should not be called in this test (build failed)" >&2
    exit 1
fi

# Default: unknown invocation
echo "ERROR: Unknown gpg invocation: $@" >&2
exit 1
''', encoding='utf-8')
    fake_gpg.chmod(0o755)


def create_fake_bumpversion(bin_dir: Path, log_file: Path, test_dir: Path) -> None:
    """Create a fake bumpversion executable that simulates version bumping."""

    fake_bumpversion = bin_dir / "bumpversion"
    fake_bumpversion.write_text(f'''#!/usr/bin/env bash
set -e

LOG_FILE="{log_file}"

# Log all invocations
echo "bumpversion $@" >> "$LOG_FILE"

# Simulate successful version bump
exit 0
''', encoding='utf-8')
    fake_bumpversion.chmod(0o755)


def test_failed_build_does_not_sign_upload_or_push(tmp_path):
    """Test that when python3 -m build fails, the script does not sign, upload, or push."""

    # Setup test directory structure
    test_dir = tmp_path / "test_release_script"
    test_dir.mkdir()

    # Create bin directory for fake executables
    bin_dir = test_dir / "bin"
    bin_dir.mkdir()

    # Create shared log file
    log_file = test_dir / "command.log"
    log_file.touch()

    # Create fake executables
    create_fake_python3(bin_dir, log_file)
    create_fake_git(bin_dir, log_file, test_dir)
    create_fake_gpg(bin_dir, log_file)
    create_fake_bumpversion(bin_dir, log_file, test_dir)

    # Copy release.sh to test directory
    project_root = Path(__file__).parent.parent
    release_script = project_root / "release.sh"
    test_release_script = test_dir / "release.sh"
    shutil.copy(release_script, test_release_script)
    test_release_script.chmod(0o755)

    # Copy required files for the script
    for file_name in ["setup.py", "setup.cfg", "README.md"]:
        src_file = project_root / file_name
        if src_file.exists():
            shutil.copy(src_file, test_dir / file_name)

    # Copy src directory structure (required for build)
    src_dir = project_root / "src"
    if src_dir.exists():
        shutil.copytree(src_dir, test_dir / "src")

    # Prepare environment
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["RELEASE_TEST_LOG"] = str(log_file)

    # Run release.sh in test mode (TestPyPI, no --production flag)
    # This avoids git push requirement during preflight
    result = subprocess.run(
        ["bash", str(test_release_script), "--key-id", "test-key-123"],
        cwd=test_dir,
        env=env,
        capture_output=True,
        text=True
    )

    # Read the command log
    command_log = log_file.read_text()

    # Assertions:

    # 1. Script should return nonzero exit code (build failed)
    assert result.returncode != 0, \
        f"Expected nonzero exit code, got {result.returncode}"

    # 2. Build was attempted
    assert "python3 -m build" in command_log, \
        f"Expected 'python3 -m build' in log, but found:\n{command_log}"

    # 3. No GPG signing invocation (--detach-sign)
    # Note: --list-secret-keys is expected for preflight check
    gpg_sign_commands = [line for line in command_log.split('\n')
                         if 'gpg' in line and '--detach-sign' in line]
    assert len(gpg_sign_commands) == 0, \
        f"Expected no GPG signing, but found:\n{chr(10).join(gpg_sign_commands)}"

    # 4. No twine check or upload invocation
    twine_commands = [line for line in command_log.split('\n')
                      if 'python3 -m twine' in line]
    assert len(twine_commands) == 0, \
        f"Expected no twine invocations, but found:\n{chr(10).join(twine_commands)}"

    # 5. No git push invocation
    # Note: git status and other preflight calls are expected
    git_push_commands = [line for line in command_log.split('\n')
                         if 'git push' in line]
    assert len(git_push_commands) == 0, \
        f"Expected no 'git push', but found:\n{chr(10).join(git_push_commands)}"

    # 6. Script does not print successful-completion message
    assert "Release completed successfully" not in result.stdout, \
        f"Expected no success message, but stdout contains:\n{result.stdout}"
    assert "Release completed successfully" not in result.stderr, \
        f"Expected no success message, but stderr contains:\n{result.stderr}"
