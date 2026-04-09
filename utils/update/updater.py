import subprocess
import sys
from typing import Optional
from utils.update.git_manager import GitManager
from utils.core.log import log_info, log_warning, log_error, log_success


class Updater:
    """Handles automatic updates for the application"""
    
    def __init__(
        self,
        branch: str = 'main',
        remote: str = 'origin',
    ):
        """
        Initialize Updater
        
        Args:
            branch: Git branch to check (default: 'main')
            remote: Git remote name (default: 'origin')
        """
        self.git_manager = GitManager()
        self.branch = branch
        self.remote = remote
        self.update_available = False
    
    def check_update(self) -> bool:
        """
        Check if update is available
        
        Returns:
            True if update available, False otherwise
        """
        if not self.git_manager.is_git_repo():
            log_warning("Not a git repository, cannot check for updates")
            return False
        
        log_info("Checking for updates...")
        available, commit = self.git_manager.check_update_available(self.branch, self.remote)
        
        if available and commit:
            self.update_available = True
            commit_info = self.git_manager.get_commit_info(commit)
            if commit_info:
                log_info(f"Update available: {commit_info['message']} ({commit[:8]})")
            else:
                log_info(f"Update available: {commit[:8]}")
            return True
        else:
            self.update_available = False
            log_info("Repository is up to date")
            return False
    
    def update(self, reset_hard: bool = True, install_dependencies: bool = True) -> bool:
        """
        Update the repository
        
        Args:
            reset_hard: If True, use 'git reset --hard' for clean update
            install_dependencies: If True, install/update Python dependencies after code update
            
        Returns:
            True if update successful, False otherwise
        """
        if not self.git_manager.is_git_repo():
            log_error("Not a git repository, cannot update")
            return False
        
        log_info("Starting update...")
        success = self.git_manager.pull_update(self.branch, self.remote, reset_hard=reset_hard)
        
        if success:
            self.update_available = False
            log_success("Code update completed successfully")
            
            # Install/update Python dependencies if requested
            if install_dependencies:
                self._install_dependencies()
        
        return success
    
    def _install_dependencies(self):
        """Install/update Python dependencies from requirements.txt"""
        requirements_file = 'requirements.txt'
        
        try:
            import os
            if not os.path.exists(requirements_file):
                log_warning(f"{requirements_file} not found, skipping dependency installation")
                return
            
            log_info("Installing/updating Python dependencies...")
            python_exe = sys.executable
            cmd = [python_exe, '-m', 'pip', 'install', '-r', requirements_file]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode == 0:
                log_success("Dependencies installed/updated successfully")
                if result.stdout.strip():
                    log_info(result.stdout.strip())
            else:
                log_error(f"Failed to install dependencies: {result.stderr}")
                log_warning("You may need to manually run: pip install -r requirements.txt")
                
        except Exception as e:
            log_error(f"Error installing dependencies: {e}")
            log_warning("You may need to manually run: pip install -r requirements.txt")


def check_and_update(branch: str = 'main', remote: str = 'origin', auto_update: bool = False, install_dependencies: bool = True) -> bool:
    """
    Check for updates and optionally update automatically
    
    Args:
        branch: Git branch to check (default: 'main')
        remote: Git remote name (default: 'origin')
        auto_update: If True, automatically update when available
        install_dependencies: If True, install/update Python dependencies after update
        
    Returns:
        True if update was applied, False otherwise
    """
    updater = Updater(branch=branch, remote=remote)
    
    # Test git first
    if not updater.git_manager.test_git():
        log_warning("Git is not available. Skipping update check.")
        return False
    
    # Check for updates
    if updater.check_update():
        if auto_update:
            return updater.update(install_dependencies=install_dependencies)
        else:
            log_info("Update available but auto_update is disabled")
            return False
    
    return False

