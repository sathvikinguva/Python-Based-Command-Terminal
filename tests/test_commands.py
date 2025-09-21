"""
Unit tests for PyTerm commands and functionality.
"""

import os
import shutil
import tempfile
from pathlib import Path
import pytest
from unittest.mock import Mock, patch

# Test imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from executor import SafeExecutor, Config, SecurityError
from commands import PWDCommand, LSCommand, CDCommand, MkdirCommand, RMCommand
from monitor import MonitorCommand


class TestConfig:
    """Test configuration management."""
    
    def test_load_config_file_not_found(self):
        """Test loading config when file doesn't exist."""
        config = Config("nonexistent.yml")
        assert config.get('safe_mode') is True  # Default value
    
    def test_get_config_value(self):
        """Test getting configuration values."""
        config = Config()
        config.config = {'test_key': 'test_value'}
        assert config.get('test_key') == 'test_value'
        assert config.get('missing_key', 'default') == 'default'


class TestSafeExecutor:
    """Test safe execution and security features."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def executor(self, temp_dir):
        """Create a SafeExecutor for testing."""
        config = Config()
        config.config = {
            'safe_mode': True,
            'allowed_root': str(temp_dir),
            'dry_run': False,
            'recycle_bin': '.recycle_bin'
        }
        return SafeExecutor(config)
    
    def test_safe_resolve_valid_path(self, executor, temp_dir):
        """Test resolving a valid path within allowed root."""
        test_file = temp_dir / "test.txt"
        test_file.touch()
        
        result = executor.safe_resolve("test.txt")
        assert result == test_file.resolve()
    
    def test_safe_resolve_invalid_path(self, executor):
        """Test resolving path outside allowed root."""
        with pytest.raises(SecurityError):
            executor.safe_resolve("/etc/passwd")
    
    def test_safe_resolve_parent_directory(self, executor):
        """Test resolving parent directory access."""
        with pytest.raises(SecurityError):
            executor.safe_resolve("../../../etc")
    
    def test_safe_delete(self, executor, temp_dir):
        """Test safe file deletion to recycle bin."""
        # Create test file
        test_file = temp_dir / "test_delete.txt"
        test_file.write_text("test content")
        
        # Delete file
        success = executor.safe_delete(test_file)
        assert success is True
        assert not test_file.exists()
        
        # Check file is in recycle bin
        recycle_bin = executor.recycle_bin
        assert recycle_bin.exists()
        recycled_files = list(recycle_bin.iterdir())
        assert len(recycled_files) == 1
        assert recycled_files[0].name == "test_delete.txt"
    
    def test_check_permissions_read(self, executor, temp_dir):
        """Test checking read permissions."""
        test_file = temp_dir / "readable.txt"
        test_file.write_text("content")
        
        assert executor.check_permissions(test_file, 'read') is True
    
    def test_validate_command_args_safe(self, executor):
        """Test validating safe command arguments."""
        safe_args = ["test.txt", "-l", "--verbose"]
        assert executor.validate_command_args(safe_args) is True
    
    def test_validate_command_args_dangerous(self, executor):
        """Test validating dangerous command arguments."""
        dangerous_args = ["../../../etc/passwd"]
        result = executor.validate_command_args(dangerous_args)
        # Should return False in safe mode
        assert result is False


class TestCommands:
    """Test command implementations."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                yield Path(tmpdir)
            finally:
                os.chdir(original_cwd)
    
    @pytest.fixture
    def executor(self, temp_dir):
        """Create a SafeExecutor for testing."""
        config = Config()
        config.config = {
            'safe_mode': True,
            'allowed_root': str(temp_dir),
            'dry_run': False,
            'recycle_bin': '.recycle_bin'
        }
        return SafeExecutor(config)
    
    def test_pwd_command(self, executor, temp_dir):
        """Test pwd command."""
        cmd = PWDCommand(executor)
        with patch.object(cmd.console, 'print') as mock_print:
            result = cmd.execute([])
            assert result is True
            mock_print.assert_called_once()
    
    def test_ls_command_empty_directory(self, executor, temp_dir):
        """Test ls command on empty directory."""
        cmd = LSCommand(executor)
        with patch.object(cmd.console, 'print') as mock_print:
            result = cmd.execute([])
            assert result is True
    
    def test_ls_command_with_files(self, executor, temp_dir):
        """Test ls command with files."""
        # Create test files
        (temp_dir / "file1.txt").touch()
        (temp_dir / "file2.txt").touch()
        (temp_dir / "subdir").mkdir()
        
        cmd = LSCommand(executor)
        with patch.object(cmd.console, 'print') as mock_print:
            result = cmd.execute([])
            assert result is True
            # Should have printed the files
            assert mock_print.call_count >= 3
    
    def test_ls_command_long_format(self, executor, temp_dir):
        """Test ls command with long format."""
        (temp_dir / "test.txt").write_text("test")
        
        cmd = LSCommand(executor)
        with patch.object(cmd.console, 'print') as mock_print:
            result = cmd.execute(["-l"])
            assert result is True
            mock_print.assert_called()
    
    def test_cd_command_valid_directory(self, executor, temp_dir):
        """Test cd command to valid directory."""
        subdir = temp_dir / "testdir"
        subdir.mkdir()
        
        cmd = CDCommand(executor)
        result = cmd.execute(["testdir"])
        assert result is True
        assert Path.cwd() == subdir
    
    def test_cd_command_invalid_directory(self, executor, temp_dir):
        """Test cd command to invalid directory."""
        cmd = CDCommand(executor)
        with patch.object(cmd.console, 'print') as mock_print:
            result = cmd.execute(["nonexistent"])
            assert result is False
            mock_print.assert_called()
    
    def test_mkdir_command_new_directory(self, executor, temp_dir):
        """Test mkdir command creating new directory."""
        cmd = MkdirCommand(executor)
        result = cmd.execute(["newdir"])
        assert result is True
        assert (temp_dir / "newdir").exists()
        assert (temp_dir / "newdir").is_dir()
    
    def test_mkdir_command_existing_directory(self, executor, temp_dir):
        """Test mkdir command on existing directory."""
        existing_dir = temp_dir / "existing"
        existing_dir.mkdir()
        
        cmd = MkdirCommand(executor)
        with patch.object(cmd.console, 'print') as mock_print:
            result = cmd.execute(["existing"])
            assert result is True  # Should succeed but warn
            mock_print.assert_called()
    
    def test_mkdir_command_parents_flag(self, executor, temp_dir):
        """Test mkdir command with -p flag."""
        cmd = MkdirCommand(executor)
        result = cmd.execute(["-p", "parent/child/grandchild"])
        assert result is True
        assert (temp_dir / "parent" / "child" / "grandchild").exists()
    
    def test_rm_command_file(self, executor, temp_dir):
        """Test rm command on file."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")
        
        cmd = RMCommand(executor)
        result = cmd.execute(["test.txt"])
        assert result is True
        assert not test_file.exists()
        
        # Check file is in recycle bin
        recycle_bin = executor.recycle_bin
        recycled_files = list(recycle_bin.iterdir())
        assert len(recycled_files) == 1
    
    def test_rm_command_directory_without_recursive(self, executor, temp_dir):
        """Test rm command on directory without -r flag."""
        test_dir = temp_dir / "testdir"
        test_dir.mkdir()
        
        cmd = RMCommand(executor)
        with patch.object(cmd.console, 'print') as mock_print:
            result = cmd.execute(["testdir"])
            assert result is False
            mock_print.assert_called()
            assert test_dir.exists()  # Should not be deleted
    
    def test_rm_command_directory_recursive(self, executor, temp_dir):
        """Test rm command on directory with -r flag."""
        test_dir = temp_dir / "testdir"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")
        
        cmd = RMCommand(executor)
        with patch('builtins.input', return_value='y'):  # Confirm deletion
            result = cmd.execute(["-r", "testdir"])
            assert result is True
            assert not test_dir.exists()
    
    def test_rm_command_nonexistent_file(self, executor, temp_dir):
        """Test rm command on nonexistent file."""
        cmd = RMCommand(executor)
        with patch.object(cmd.console, 'print') as mock_print:
            result = cmd.execute(["nonexistent.txt"])
            assert result is False
            mock_print.assert_called()


class TestMonitorCommand:
    """Test monitor command."""
    
    @pytest.fixture
    def executor(self):
        """Create a mock executor for testing."""
        config = Config()
        config.config = {'max_processes_display': 5}
        return SafeExecutor(config)
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.boot_time')
    def test_monitor_command_basic(self, mock_boot_time, mock_memory, mock_cpu, executor):
        """Test basic monitor command functionality."""
        # Mock psutil returns
        mock_cpu.return_value = 25.5
        mock_memory.return_value = Mock(percent=60.0, used=8000000000, total=16000000000)
        mock_boot_time.return_value = 1640000000
        
        cmd = MonitorCommand(executor)
        with patch.object(cmd.console, 'print') as mock_print:
            result = cmd.execute([])
            assert result is True
            mock_print.assert_called()


class TestIntegration:
    """Integration tests for the full system."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for integration tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                yield Path(tmpdir)
            finally:
                os.chdir(original_cwd)
    
    def test_command_chain(self, temp_workspace):
        """Test a chain of commands working together."""
        # Set up executor
        config = Config()
        config.config = {
            'safe_mode': True,
            'allowed_root': str(temp_workspace),
            'dry_run': False,
            'recycle_bin': '.recycle_bin'
        }
        executor = SafeExecutor(config)
        
        # Create commands
        mkdir_cmd = MkdirCommand(executor)
        ls_cmd = LSCommand(executor)
        cd_cmd = CDCommand(executor)
        rm_cmd = RMCommand(executor)
        
        # Test sequence: mkdir -> ls -> cd -> rm
        assert mkdir_cmd.execute(["testdir"]) is True
        assert (temp_workspace / "testdir").exists()
        
        with patch.object(ls_cmd.console, 'print'):
            assert ls_cmd.execute([]) is True
        
        assert cd_cmd.execute(["testdir"]) is True
        assert Path.cwd().name == "testdir"
        
        # Go back to parent
        assert cd_cmd.execute(["../"]) is True
        
        # Remove directory
        with patch('builtins.input', return_value='y'):
            assert rm_cmd.execute(["-r", "testdir"]) is True
        
        assert not (temp_workspace / "testdir").exists()


if __name__ == "__main__":
    pytest.main([__file__])