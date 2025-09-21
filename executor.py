"""
Safety and security utilities for PyTerm.
Handles path validation, permission checks, and safe execution.
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
import yaml


class SecurityError(Exception):
    """Raised when a security violation is detected."""
    pass


class Config:
    """Configuration management for PyTerm."""
    
    def __init__(self, config_path: str = "config.yml"):
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logging.warning(f"Config file {self.config_path} not found, using defaults")
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            'safe_mode': True,
            'allowed_root': '.',
            'dry_run': False,
            'recycle_bin': '.recycle_bin',
            'ai_enabled': False,
            'ai_confirmation_required': True,
            'colors_enabled': True,
            'log_level': 'INFO'
        }
    
    def get(self, key: str, default=None):
        """Get configuration value."""
        return self.config.get(key, default)


class SafeExecutor:
    """Safe execution environment for commands."""
    
    def __init__(self, config: Config):
        self.config = config
        self.allowed_root = Path(config.get('allowed_root', '.')).resolve()
        self.recycle_bin = self.allowed_root / config.get('recycle_bin', '.recycle_bin')
        self.dry_run = config.get('dry_run', False)
        
        # Ensure recycle bin exists
        self.recycle_bin.mkdir(exist_ok=True)
        
        # Set up logging
        logging.basicConfig(
            level=getattr(logging, config.get('log_level', 'INFO')),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def safe_resolve(self, path_str: str) -> Path:
        """
        Safely resolve a path, ensuring it's within allowed_root.
        
        Args:
            path_str: Path string to resolve
            
        Returns:
            Resolved Path object
            
        Raises:
            SecurityError: If path is outside allowed root
        """
        try:
            # Handle relative and absolute paths
            if os.path.isabs(path_str):
                path = Path(path_str)
            else:
                path = Path.cwd() / path_str
            
            # Resolve and normalize
            resolved = path.resolve()
            
            # Check if within allowed root
            try:
                resolved.relative_to(self.allowed_root)
            except ValueError:
                raise SecurityError(f"Access denied: {resolved} is outside allowed root {self.allowed_root}")
            
            return resolved
            
        except Exception as e:
            if isinstance(e, SecurityError):
                raise
            raise SecurityError(f"Invalid path: {path_str} - {e}")
    
    def safe_delete(self, path: Path) -> bool:
        """
        Safely delete a file or directory by moving to recycle bin.
        
        Args:
            path: Path to delete
            
        Returns:
            True if successful, False otherwise
        """
        if self.dry_run:
            self.logger.info(f"DRY RUN: Would move {path} to recycle bin")
            return True
        
        try:
            # Generate unique name in recycle bin
            dest_name = path.name
            counter = 1
            dest = self.recycle_bin / dest_name
            
            while dest.exists():
                name_parts = path.stem, counter, path.suffix
                dest_name = f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
                dest = self.recycle_bin / dest_name
                counter += 1
            
            # Move to recycle bin
            shutil.move(str(path), str(dest))
            self.logger.info(f"Moved {path} to recycle bin as {dest}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete {path}: {e}")
            return False
    
    def check_permissions(self, path: Path, operation: str) -> bool:
        """
        Check if operation is permitted on path.
        
        Args:
            path: Path to check
            operation: Operation type ('read', 'write', 'delete')
            
        Returns:
            True if permitted, False otherwise
        """
        if not path.exists():
            return operation in ['write']  # Can create new files
        
        if operation == 'read':
            return os.access(path, os.R_OK)
        elif operation == 'write':
            return os.access(path, os.W_OK)
        elif operation == 'delete':
            return os.access(path, os.W_OK) and os.access(path.parent, os.W_OK)
        
        return False
    
    def validate_command_args(self, args: list, expected_types: list = None) -> bool:
        """
        Validate command arguments.
        
        Args:
            args: Arguments to validate
            expected_types: Expected types for arguments
            
        Returns:
            True if valid, False otherwise
        """
        if expected_types and len(args) != len(expected_types):
            return False
        
        # Basic sanitization - check for dangerous patterns
        dangerous_patterns = ['../', '~/', '/etc/', '/sys/', '/proc/']
        
        for arg in args:
            if isinstance(arg, str):
                arg_lower = arg.lower()
                for pattern in dangerous_patterns:
                    if pattern in arg_lower:
                        self.logger.warning(f"Potentially dangerous argument: {arg}")
                        return self.config.get('safe_mode', True) == False
        
        return True