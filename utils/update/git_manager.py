import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple
from utils.core.log import log_info, log_warning, log_error, log_success


class GitManager:
    """Manages Git operations with support for bundled Git executable"""
    
    def __init__(self, git_executable: Optional[str] = None):
        """
        Initialize GitManager
        
        Args:
            git_executable: Path to git executable. If None, will auto-detect:
                1. Bundled git in ./toolkit/Git/
                2. System git in PATH
        """
        self.git_executable = git_executable or self._find_git()
        self.project_root = self._get_project_root()
        
    def _get_project_root(self) -> Path:
        """Get the project root directory"""
        # Try to find .git directory by walking up from current file
        current = Path(__file__).parent.parent.absolute()
        while current != current.parent:
            if (current / '.git').exists():
                return current
            current = current.parent
        # Fallback to current working directory
        return Path.cwd()
    
    def _find_git(self) -> str:
        """
        Find git executable with fallback priority:
        1. Bundled git in ./toolkit/Git/
        2. System git in PATH
        """
        # Try bundled git first (Windows)
        if sys.platform == 'win32':
            bundled_paths = [
                './toolkit/Git/mingw64/bin/git.exe',
                './toolkit/Git/cmd/git.exe',
                './toolkit/Git/bin/git.exe',
            ]
            for path in bundled_paths:
                full_path = os.path.abspath(path)
                if os.path.exists(full_path):
                    log_info(f"Using bundled Git: {full_path}")
                    return full_path
        
        # Try bundled git (Linux/Mac)
        bundled_paths = [
            './toolkit/Git/bin/git',
            './toolkit/git',
        ]
        for path in bundled_paths:
            full_path = os.path.abspath(path)
            if os.path.exists(full_path) and os.access(full_path, os.X_OK):
                log_info(f"Using bundled Git: {full_path}")
                return full_path
        
        # Fallback to system git
        log_info("Bundled Git not found, using system git (must be in PATH)")
        return 'git'
    
    def _execute(self, command: list, cwd: Optional[Path] = None, allow_failure: bool = False) -> Tuple[bool, str, str]:
        """
        Execute git command
        
        Args:
            command: Git command as list (e.g., ['pull', 'origin', 'main'])
            cwd: Working directory (default: project root)
            allow_failure: If True, don't raise exception on failure
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        cwd = cwd or self.project_root
        full_command = [self.git_executable] + command
        
        try:
            log_info(f"Executing: {' '.join(full_command)}")
            result = subprocess.run(
                full_command,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode == 0:
                return True, result.stdout, result.stderr
            else:
                if not allow_failure:
                    log_error(f"Git command failed: {result.stderr}")
                return False, result.stdout, result.stderr
                
        except FileNotFoundError:
            error_msg = f"Git executable not found: {self.git_executable}"
            if not allow_failure:
                log_error(error_msg)
            return False, "", error_msg
        except Exception as e:
            error_msg = f"Error executing git command: {str(e)}"
            if not allow_failure:
                log_error(error_msg)
            return False, "", error_msg
    
    def check_update_available(self, branch: str = 'main', remote: str = 'origin') -> Tuple[bool, Optional[str]]:
        """
        Check if update is available from remote repository
        
        Args:
            branch: Branch name to check (default: 'main')
            remote: Remote name (default: 'origin')
            
        Returns:
            Tuple of (update_available, latest_commit_hash)
        """
        # Fetch latest from remote
        success, _, _ = self._execute(['fetch', remote, branch], allow_failure=True)
        if not success:
            log_warning("Failed to fetch from remote, cannot check for updates")
            return False, None
        
        # Get local commit
        success, local_commit, _ = self._execute(['rev-parse', 'HEAD'], allow_failure=True)
        if not success:
            log_warning("Failed to get local commit")
            return False, None
        local_commit = local_commit.strip()
        
        # Get remote commit
        success, remote_commit, _ = self._execute(['rev-parse', f'{remote}/{branch}'], allow_failure=True)
        if not success:
            log_warning("Failed to get remote commit")
            return False, None
        remote_commit = remote_commit.strip()
        
        # Compare commits
        if local_commit == remote_commit:
            log_info("Repository is up to date")
            return False, remote_commit
        
        # Check if local commit exists in remote
        success, _, _ = self._execute(['branch', '--contains', remote_commit], allow_failure=True)
        if success:
            log_info(f"Update available: {remote_commit[:8]}")
            return True, remote_commit
        
        # Local has commits not in remote (developer mode)
        log_warning("Local repository has commits not in remote, skipping update")
        return False, None
    
    def pull_update(self, branch: str = 'main', remote: str = 'origin', reset_hard: bool = False) -> bool:
        """
        Pull updates from remote repository
        
        Args:
            branch: Branch name to pull (default: 'main')
            remote: Remote name (default: 'origin')
            reset_hard: If True, use 'git reset --hard' instead of 'git pull'
            
        Returns:
            True if update successful, False otherwise
        """
        # Remove git lock files if they exist
        lock_files = [
            '.git/index.lock',
            '.git/HEAD.lock',
            f'.git/refs/heads/{branch}.lock',
        ]
        for lock_file in lock_files:
            lock_path = self.project_root / lock_file
            if lock_path.exists():
                log_info(f"Removing lock file: {lock_file}")
                try:
                    lock_path.unlink()
                except Exception as e:
                    log_warning(f"Failed to remove lock file {lock_file}: {e}")
        
        if reset_hard:
            # Use reset --hard for clean update
            log_info(f"Resetting to {remote}/{branch}...")
            success, _, _ = self._execute(['reset', '--hard', f'{remote}/{branch}'])
            if success:
                log_success("Repository updated successfully")
            return success
        else:
            # Use pull for merge-based update
            log_info(f"Pulling from {remote}/{branch}...")
            success, stdout, stderr = self._execute(['pull', '--ff-only', remote, branch])
            if success:
                log_success("Repository updated successfully")
                if stdout.strip():
                    log_info(stdout.strip())
            else:
                log_error(f"Failed to pull updates: {stderr}")
            return success
    
    def get_current_commit(self, short: bool = False) -> Optional[str]:
        """
        Get current commit hash
        
        Args:
            short: If True, return short hash (8 chars)
            
        Returns:
            Commit hash or None if failed
        """
        command = ['rev-parse', '--short', 'HEAD'] if short else ['rev-parse', 'HEAD']
        success, commit, _ = self._execute(command, allow_failure=True)
        if success:
            return commit.strip()
        return None
    
    def get_commit_info(self, commit: Optional[str] = None) -> Optional[dict]:
        """
        Get commit information
        
        Args:
            commit: Commit hash (default: HEAD)
            
        Returns:
            Dict with commit info or None if failed
        """
        commit = commit or 'HEAD'
        success, output, _ = self._execute(
            ['log', '-1', '--pretty=format:%H---%an---%ad---%s', '--date=iso', commit],
            allow_failure=True
        )
        
        if not success:
            return None
        
        try:
            parts = output.strip().split('---')
            if len(parts) == 4:
                return {
                    'hash': parts[0],
                    'author': parts[1],
                    'date': parts[2],
                    'message': parts[3]
                }
        except Exception as e:
            log_warning(f"Failed to parse commit info: {e}")
        
        return None
    
    def is_git_repo(self) -> bool:
        """Check if current directory is a git repository"""
        return (self.project_root / '.git').exists()
    
    def test_git(self) -> bool:
        """Test if git executable is working"""
        success, version, _ = self._execute(['--version'], allow_failure=True)
        if success:
            log_info(f"Git version: {version.strip()}")
            return True
        else:
            log_error("Git is not working or not found")
            return False

