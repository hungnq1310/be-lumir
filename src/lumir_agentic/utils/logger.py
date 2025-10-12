"""
Professional Logger for Lumir Agentic System
Provides colored, timestamped logging with proper log levels
"""

import logging
import sys
from datetime import datetime
from enum import Enum
from typing import Optional

try:
    from colorama import Fore, Back, Style, init
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    # Fallback color codes for systems without colorama
    class Fore:
        RED = '\033[31m'
        GREEN = '\033[32m'
        YELLOW = '\033[33m'
        BLUE = '\033[34m'
        MAGENTA = '\033[35m'
        CYAN = '\033[36m'
        WHITE = '\033[37m'
        RESET = '\033[0m'
    
    class Style:
        BRIGHT = '\033[1m'
        RESET_ALL = '\033[0m'


class LogLevel(Enum):
    """Log levels with associated colors and priorities"""
    DEBUG = ("DEBUG", Fore.CYAN, 10)
    INFO = ("INFO", Fore.GREEN, 20)
    WARNING = ("WARNING", Fore.YELLOW, 30)
    ERROR = ("ERROR", Fore.RED, 40)
    CRITICAL = ("CRITICAL", Fore.MAGENTA, 50)
    
    def __init__(self, name: str, color: str, level: int):
        self.level_name = name
        self.color = color
        self.level = level


class LogCategory(Enum):
    """Log categories for different system components"""
    SYSTEM = ("SYSTEM", Fore.BLUE)
    AGENT = ("AGENT", Fore.GREEN)
    REASONING = ("REASONING", Fore.CYAN)
    PLANNING = ("PLANNING", Fore.YELLOW)
    EXECUTION = ("EXECUTION", Fore.MAGENTA)
    TOOL = ("TOOL", Fore.WHITE)
    RESPONSE = ("RESPONSE", Fore.GREEN)
    CONFIG = ("CONFIG", Fore.BLUE)
    SESSION = ("SESSION", Fore.CYAN)
    
    def __init__(self, name: str, color: str):
        self.category_name = name
        self.color = color


class LumirLogger:
    """Professional logger for Lumir Agentic System"""
    
    def __init__(self, name: str = "LumirAgent", level: LogLevel = LogLevel.INFO, display_enabled: bool = True):
        self.name = name
        self.level = level
        self.display_enabled = display_enabled
        self._setup_python_logger()
    
    def _setup_python_logger(self):
        """Setup Python's built-in logger for file logging"""
        self.python_logger = logging.getLogger(self.name)
        self.python_logger.setLevel(self.level.level)
        
        # Create file handler if not exists
        if not self.python_logger.handlers:
            handler = logging.FileHandler('lumir_agent.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.python_logger.addHandler(handler)
    
    def _get_timestamp(self) -> str:
        """Get formatted timestamp"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _format_message(self, level: LogLevel, category: LogCategory, message: str, details: Optional[str] = None) -> str:
        """Format log message with colors and structure"""
        timestamp = self._get_timestamp()
        
        if self.display_enabled:
            # Colored console output
            formatted = (
                f"{Style.BRIGHT}{timestamp}{Style.RESET_ALL} "
                f"[{level.color}{level.level_name}{Style.RESET_ALL}] "
                f"[{category.color}{category.category_name}{Style.RESET_ALL}] "
                f"{message}"
            )
            
            if details:
                formatted += f" - {Fore.WHITE}{details}{Style.RESET_ALL}"
        else:
            # Plain text output
            formatted = f"{timestamp} [{level.level_name}] [{category.category_name}] {message}"
            if details:
                formatted += f" - {details}"
        
        return formatted
    
    def _log(self, level: LogLevel, category: LogCategory, message: str, details: Optional[str] = None):
        """Internal logging method"""
        if level.level >= self.level.level:
            formatted_message = self._format_message(level, category, message, details)
            print(formatted_message)
            
            # Also log to file via Python logger
            plain_message = f"[{category.category_name}] {message}"
            if details:
                plain_message += f" - {details}"
            
            if level == LogLevel.DEBUG:
                self.python_logger.debug(plain_message)
            elif level == LogLevel.INFO:
                self.python_logger.info(plain_message)
            elif level == LogLevel.WARNING:
                self.python_logger.warning(plain_message)
            elif level == LogLevel.ERROR:
                self.python_logger.error(plain_message)
            elif level == LogLevel.CRITICAL:
                self.python_logger.critical(plain_message)
    
    # System logging methods
    def system_info(self, message: str, details: Optional[str] = None):
        """Log system information"""
        self._log(LogLevel.INFO, LogCategory.SYSTEM, message, details)
    
    def system_error(self, message: str, details: Optional[str] = None):
        """Log system error"""
        self._log(LogLevel.ERROR, LogCategory.SYSTEM, message, details)
    
    def system_warning(self, message: str, details: Optional[str] = None):
        """Log system warning"""
        self._log(LogLevel.WARNING, LogCategory.SYSTEM, message, details)
    
    # Agent logging methods
    def agent_start(self, message: str = "Starting processing", details: Optional[str] = None):
        """Log agent start"""
        self._log(LogLevel.INFO, LogCategory.AGENT, message, details)
    
    def agent_complete(self, message: str = "Processing completed", details: Optional[str] = None):
        """Log agent completion"""
        self._log(LogLevel.INFO, LogCategory.AGENT, message, details)
    
    def agent_error(self, message: str, details: Optional[str] = None):
        """Log agent error"""
        self._log(LogLevel.ERROR, LogCategory.AGENT, message, details)
    
    # Reasoning logging methods
    def reasoning_start(self, message: str = "Analyzing question", details: Optional[str] = None):
        """Log reasoning start"""
        self._log(LogLevel.INFO, LogCategory.REASONING, message, details)
    
    def reasoning_complete(self, strategy: str, details: Optional[str] = None):
        """Log reasoning completion"""
        self._log(LogLevel.INFO, LogCategory.REASONING, f"Completed: {strategy}", details)
    
    # Planning logging methods
    def planning_start(self, message: str = "Creating execution plan", details: Optional[str] = None):
        """Log planning start"""
        self._log(LogLevel.INFO, LogCategory.PLANNING, message, details)
    
    def planning_complete(self, steps: int, tools: int, details: Optional[str] = None):
        """Log planning completion"""
        self._log(LogLevel.INFO, LogCategory.PLANNING, f"Completed: {steps} steps, {tools} tools", details)
    
    # Execution logging methods
    def execution_start(self, message: str = "Executing plan", details: Optional[str] = None):
        """Log execution start"""
        self._log(LogLevel.INFO, LogCategory.EXECUTION, message, details)
    
    def execution_complete(self, tool_count: int, details: Optional[str] = None):
        """Log execution completion"""
        self._log(LogLevel.INFO, LogCategory.EXECUTION, f"Completed {tool_count} tool calls", details)
    
    # Tool logging methods
    def tool_start(self, tool_name: str, details: Optional[str] = None):
        """Log tool execution start"""
        self._log(LogLevel.INFO, LogCategory.TOOL, f"Executing {tool_name}", details)
    
    def tool_complete(self, tool_name: str, details: Optional[str] = None):
        """Log tool execution completion"""
        self._log(LogLevel.INFO, LogCategory.TOOL, f"{tool_name} completed successfully", details)
    
    def tool_error(self, tool_name: str, error: str, details: Optional[str] = None):
        """Log tool execution error"""
        self._log(LogLevel.ERROR, LogCategory.TOOL, f"{tool_name} failed: {error}", details)
    
    def tool_result(self, tool_name: str, result_preview: str, details: Optional[str] = None):
        """Log tool result"""
        self._log(LogLevel.DEBUG, LogCategory.TOOL, f"{tool_name} result: {result_preview}", details)
    
    # Response logging methods
    def response_start(self, message: str = "Generating final response", details: Optional[str] = None):
        """Log response generation start"""
        self._log(LogLevel.INFO, LogCategory.RESPONSE, message, details)
    
    def response_complete(self, message: str = "Response generation completed", details: Optional[str] = None):
        """Log response generation completion"""
        self._log(LogLevel.INFO, LogCategory.RESPONSE, message, details)
    
    # Configuration logging methods
    def config_loaded(self, message: str, details: Optional[str] = None):
        """Log configuration loaded"""
        self._log(LogLevel.INFO, LogCategory.CONFIG, message, details)
    
    def config_error(self, message: str, details: Optional[str] = None):
        """Log configuration error"""
        self._log(LogLevel.ERROR, LogCategory.CONFIG, message, details)
    
    # Session logging methods
    def session_created(self, session_id: str, details: Optional[str] = None):
        """Log session creation"""
        self._log(LogLevel.INFO, LogCategory.SESSION, f"Session created: {session_id}", details)
    
    def session_loaded(self, profile_name: str, details: Optional[str] = None):
        """Log session profile loaded"""
        self._log(LogLevel.INFO, LogCategory.SESSION, f"Profile loaded: {profile_name}", details)
    
    # User interaction logging
    def user_question(self, question: str, details: Optional[str] = None):
        """Log user question"""
        self._log(LogLevel.INFO, LogCategory.SYSTEM, f"User question: {question}", details)
    
    def agent_response(self, response_preview: str, details: Optional[str] = None):
        """Log agent response"""
        preview = response_preview[:10000] + "..." if len(response_preview) > 100 else response_preview
        self._log(LogLevel.INFO, LogCategory.AGENT, f"Response: {preview}", details)
    
    # Generic logging methods
    def debug(self, message: str, category: LogCategory = LogCategory.SYSTEM, details: Optional[str] = None):
        """Log debug message"""
        self._log(LogLevel.DEBUG, category, message, details)
    
    def info(self, message: str, category: LogCategory = LogCategory.SYSTEM, details: Optional[str] = None):
        """Log info message"""
        self._log(LogLevel.INFO, category, message, details)
    
    def warning(self, message: str, category: LogCategory = LogCategory.SYSTEM, details: Optional[str] = None):
        """Log warning message"""
        self._log(LogLevel.WARNING, category, message, details)
    
    def error(self, message: str, category: LogCategory = LogCategory.SYSTEM, details: Optional[str] = None):
        """Log error message"""
        self._log(LogLevel.ERROR, category, message, details)
    
    def critical(self, message: str, category: LogCategory = LogCategory.SYSTEM, details: Optional[str] = None):
        """Log critical message"""
        self._log(LogLevel.CRITICAL, category, message, details)


# Global logger instance
logger = LumirLogger()

# Convenience functions for backward compatibility
def log_system_info(message: str, details: Optional[str] = None):
    logger.system_info(message, details)

def log_agent_start(message: str = "Starting processing", details: Optional[str] = None):
    logger.agent_start(message, details)

def log_agent_complete(message: str = "Processing completed", details: Optional[str] = None):
    logger.agent_complete(message, details)

def log_reasoning_start(message: str = "Analyzing question", details: Optional[str] = None):
    logger.reasoning_start(message, details)

def log_reasoning_complete(strategy: str, details: Optional[str] = None):
    logger.reasoning_complete(strategy, details)

def log_planning_start(message: str = "Creating execution plan", details: Optional[str] = None):
    logger.planning_start(message, details)

def log_planning_complete(steps: int, tools: int, details: Optional[str] = None):
    logger.planning_complete(steps, tools, details)

def log_execution_start(message: str = "Executing plan", details: Optional[str] = None):
    logger.execution_start(message, details)

def log_execution_complete(tool_count: int, details: Optional[str] = None):
    logger.execution_complete(tool_count, details)

def log_tool_start(tool_name: str, details: Optional[str] = None):
    logger.tool_start(tool_name, details)

def log_tool_complete(tool_name: str, details: Optional[str] = None):
    logger.tool_complete(tool_name, details)

def log_tool_result(tool_name: str, result_preview: str, details: Optional[str] = None):
    logger.tool_result(tool_name, result_preview, details)

def log_response_start(message: str = "Generating final response", details: Optional[str] = None):
    logger.response_start(message, details)

def log_response_complete(message: str = "Response generation completed", details: Optional[str] = None):
    logger.response_complete(message, details)

def log_config_loaded(message: str, details: Optional[str] = None):
    logger.config_loaded(message, details)

def log_session_created(session_id: str, details: Optional[str] = None):
    logger.session_created(session_id, details)

def log_session_loaded(profile_name: str, details: Optional[str] = None):
    logger.session_loaded(profile_name, details)

def log_user_question(question: str, details: Optional[str] = None):
    logger.user_question(question, details)

def log_agent_response(response_preview: str, details: Optional[str] = None):
    logger.agent_response(response_preview, details)