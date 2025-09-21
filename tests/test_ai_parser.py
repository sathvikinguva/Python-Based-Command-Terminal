"""
Tests for AI natural language parsing functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from executor import SafeExecutor, Config
from nl_parser import AIParser, AICommand


class TestAIParser:
    """Test AI natural language parser."""
    
    @pytest.fixture
    def mock_executor(self):
        """Create a mock executor for testing."""
        config = Config()
        config.config = {
            'ai_enabled': True,
            'google_api_key': 'test_key',
            'ai_confirmation_required': False
        }
        return SafeExecutor(config)
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_ai_parser_init_with_api_key(self, mock_model_class, mock_configure, mock_executor):
        """Test AI parser initialization with API key."""
        mock_model = Mock()
        mock_model_class.return_value = mock_model
        
        parser = AIParser(mock_executor)
        
        mock_configure.assert_called_once()
        mock_model_class.assert_called_once_with('gemini-pro')
        assert parser.ai_enabled is True
    
    def test_ai_parser_init_without_api_key(self, mock_executor):
        """Test AI parser initialization without API key."""
        mock_executor.config.config['google_api_key'] = ''
        
        with patch.dict(os.environ, {}, clear=True):
            parser = AIParser(mock_executor)
            # Should still work with the hardcoded key
            assert parser.ai_enabled is not None
    
    def test_fallback_parse_list_files(self, mock_executor):
        """Test fallback parser for listing files."""
        parser = AIParser(mock_executor)
        
        commands = parser._fallback_parse("list files")
        assert commands == ["ls"]
        
        commands = parser._fallback_parse("show files")
        assert commands == ["ls"]
    
    def test_fallback_parse_create_folder(self, mock_executor):
        """Test fallback parser for creating folders."""
        parser = AIParser(mock_executor)
        
        commands = parser._fallback_parse("create folder test")
        assert commands == ["mkdir test"]
        
        commands = parser._fallback_parse("make directory mydir")
        assert commands == ["mkdir mydir"]
    
    def test_fallback_parse_change_directory(self, mock_executor):
        """Test fallback parser for changing directory."""
        parser = AIParser(mock_executor)
        
        commands = parser._fallback_parse("go to documents")
        assert commands == ["cd documents"]
        
        commands = parser._fallback_parse("change to home")
        assert commands == ["cd home"]
    
    def test_fallback_parse_remove_files(self, mock_executor):
        """Test fallback parser for removing files."""
        parser = AIParser(mock_executor)
        
        commands = parser._fallback_parse("delete file.txt")
        assert commands == ["rm file.txt"]
        
        commands = parser._fallback_parse("remove test.txt")
        assert commands == ["rm test.txt"]
    
    def test_fallback_parse_system_info(self, mock_executor):
        """Test fallback parser for system information."""
        parser = AIParser(mock_executor)
        
        commands = parser._fallback_parse("system info")
        assert commands == ["monitor"]
        
        commands = parser._fallback_parse("show stats")
        assert commands == ["monitor"]
    
    def test_fallback_parse_help(self, mock_executor):
        """Test fallback parser for help."""
        parser = AIParser(mock_executor)
        
        commands = parser._fallback_parse("help")
        assert commands == ["help"]
        
        commands = parser._fallback_parse("show help")
        assert commands == ["help"]
    
    def test_fallback_parse_unknown(self, mock_executor):
        """Test fallback parser for unknown commands."""
        parser = AIParser(mock_executor)
        
        commands = parser._fallback_parse("completely unknown command")
        assert commands == []
    
    def test_is_safe_command_valid(self, mock_executor):
        """Test safe command validation for valid commands."""
        parser = AIParser(mock_executor)
        
        assert parser._is_safe_command("ls") is True
        assert parser._is_safe_command("cd documents") is True
        assert parser._is_safe_command("mkdir test") is True
        assert parser._is_safe_command("rm file.txt") is True
    
    def test_is_safe_command_invalid(self, mock_executor):
        """Test safe command validation for invalid commands."""
        parser = AIParser(mock_executor)
        
        assert parser._is_safe_command("format C:") is False
        assert parser._is_safe_command("sudo rm -rf /") is False
        assert parser._is_safe_command("") is False
    
    def test_is_safe_command_dangerous_rm(self, mock_executor):
        """Test safe command validation for dangerous rm commands."""
        parser = AIParser(mock_executor)
        
        assert parser._is_safe_command("rm *") is False
        assert parser._is_safe_command("rm /") is False
        assert parser._is_safe_command("rm C:\\\\") is False
        assert parser._is_safe_command("rm system32") is False
    
    def test_extract_commands_markdown(self, mock_executor):
        """Test extracting commands from markdown-formatted response."""
        parser = AIParser(mock_executor)
        
        response = """```
ls -l
cd documents
mkdir test
```"""
        
        commands = parser._extract_commands(response)
        assert len(commands) == 3
        assert "ls -l" in commands
        assert "cd documents" in commands
        assert "mkdir test" in commands
    
    def test_extract_commands_unsafe_request(self, mock_executor):
        """Test extracting commands when response indicates unsafe request."""
        parser = AIParser(mock_executor)
        
        response = "UNSAFE_REQUEST"
        
        commands = parser._extract_commands(response)
        assert commands == []


class TestAICommand:
    """Test AI command execution."""
    
    @pytest.fixture
    def mock_executor(self):
        """Create a mock executor for testing."""
        config = Config()
        config.config = {
            'ai_enabled': True,
            'ai_confirmation_required': False
        }
        return SafeExecutor(config)
    
    @pytest.fixture
    def mock_commands(self):
        """Create mock command registry."""
        mock_ls = Mock()
        mock_ls.execute.return_value = True
        
        mock_cd = Mock()
        mock_cd.execute.return_value = True
        
        return {
            'ls': mock_ls,
            'cd': mock_cd
        }
    
    def test_ai_command_no_args(self, mock_executor, mock_commands):
        """Test AI command without arguments."""
        cmd = AICommand(mock_executor, mock_commands)
        
        with patch.object(cmd.console, 'print') as mock_print:
            result = cmd.execute([])
            assert result is False
            mock_print.assert_called()
    
    @patch('rich.prompt.Confirm.ask')
    def test_ai_command_with_confirmation(self, mock_confirm, mock_executor, mock_commands):
        """Test AI command with confirmation required."""
        mock_executor.config.config['ai_confirmation_required'] = True
        mock_confirm.return_value = True
        
        cmd = AICommand(mock_executor, mock_commands)
        cmd.ai_parser = Mock()
        cmd.ai_parser.parse_natural_language.return_value = ["ls", "cd documents"]
        
        with patch.object(cmd.console, 'print'):
            result = cmd.execute(["list files and go to documents"])
            assert result is True
            mock_confirm.assert_called_once()
    
    @patch('rich.prompt.Confirm.ask')
    def test_ai_command_cancelled(self, mock_confirm, mock_executor, mock_commands):
        """Test AI command cancelled by user."""
        mock_executor.config.config['ai_confirmation_required'] = True
        mock_confirm.return_value = False
        
        cmd = AICommand(mock_executor, mock_commands)
        cmd.ai_parser = Mock()
        cmd.ai_parser.parse_natural_language.return_value = ["ls"]
        
        with patch.object(cmd.console, 'print') as mock_print:
            result = cmd.execute(["list files"])
            assert result is True  # Returns True but doesn't execute
            mock_confirm.assert_called_once()
            # Should print cancelled message
            assert any("Cancelled" in str(call) for call in mock_print.call_args_list)
    
    def test_execute_command_sequence(self, mock_executor, mock_commands):
        """Test executing a sequence of commands."""
        cmd = AICommand(mock_executor, mock_commands)
        
        with patch.object(cmd.console, 'print'):
            result = cmd._execute_command_sequence(["ls", "cd documents"])
            assert result is True
            
            # Verify commands were called
            mock_commands['ls'].execute.assert_called_once_with([])
            mock_commands['cd'].execute.assert_called_once_with(["documents"])
    
    def test_execute_command_sequence_unknown_command(self, mock_executor, mock_commands):
        """Test executing sequence with unknown command."""
        cmd = AICommand(mock_executor, mock_commands)
        
        with patch.object(cmd.console, 'print') as mock_print:
            result = cmd._execute_command_sequence(["unknown_command"])
            assert result is False
            # Should print error about unknown command
            assert any("Unknown command" in str(call) for call in mock_print.call_args_list)
    
    def test_execute_command_sequence_command_fails(self, mock_executor, mock_commands):
        """Test executing sequence when a command fails."""
        mock_commands['ls'].execute.return_value = False
        
        cmd = AICommand(mock_executor, mock_commands)
        
        with patch.object(cmd.console, 'print'):
            result = cmd._execute_command_sequence(["ls"])
            assert result is False


if __name__ == "__main__":
    pytest.main([__file__])