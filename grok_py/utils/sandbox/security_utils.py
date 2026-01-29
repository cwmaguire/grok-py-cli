"""Security utilities for code execution sandbox."""

import hashlib
import json
import logging
import os
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False
import re
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from enum import Enum

logger = logging.getLogger(__name__)


class SecurityEventType(Enum):
    """Types of security events."""
    CODE_EXECUTION_START = "code_execution_start"
    CODE_EXECUTION_END = "code_execution_end"
    CONTAINER_ANOMALY = "container_anomaly"
    RESOURCE_VIOLATION = "resource_violation"
    NETWORK_ATTEMPT = "network_attempt"
    FILESYSTEM_VIOLATION = "filesystem_violation"
    MALICIOUS_PATTERN = "malicious_pattern"


@dataclass
class SecurityEvent:
    """Represents a security event."""
    event_type: SecurityEventType
    timestamp: datetime
    container_id: str
    language: str
    code_hash: str
    details: Dict[str, Any]
    severity: str = "info"  # info, warning, error, critical

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class CodeAnalysis:
    """Results of code analysis for security."""
    has_shell_commands: bool = False
    has_network_calls: bool = False
    has_file_operations: bool = False
    has_system_calls: bool = False
    has_imports: bool = False
    suspicious_patterns: List[str] = None
    risk_score: int = 0  # 0-10 scale

    def __post_init__(self):
        if self.suspicious_patterns is None:
            self.suspicious_patterns = []


class AuditLogger:
    """Handles audit logging for code executions."""

    def __init__(self, log_dir: Optional[str] = None):
        self.log_dir = Path(log_dir) if log_dir else Path.home() / ".grok" / "audit_logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_log_file = None
        self._rotate_log_file()

    def _rotate_log_file(self) -> None:
        """Rotate to a new log file if needed."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"audit_{today}.jsonl"

        if self.current_log_file != log_file:
            self.current_log_file = log_file

    def log_event(self, event: SecurityEvent) -> None:
        """Log a security event."""
        self._rotate_log_file()

        try:
            with open(self.current_log_file, 'a', encoding='utf-8') as f:
                json.dump(event.to_dict(), f)
                f.write('\n')
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")

    def get_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[SecurityEventType] = None,
        container_id: Optional[str] = None
    ) -> List[SecurityEvent]:
        """Retrieve logged events with optional filtering."""
        events = []

        try:
            # Find relevant log files
            log_files = []
            if start_date and end_date:
                current_date = start_date
                while current_date <= end_date:
                    log_file = self.log_dir / f"audit_{current_date.strftime('%Y-%m-%d')}.jsonl"
                    if log_file.exists():
                        log_files.append(log_file)
                    current_date = current_date.replace(day=current_date.day + 1)
            else:
                # Get today's log file
                today = datetime.now().strftime("%Y-%m-%d")
                log_file = self.log_dir / f"audit_{today}.jsonl"
                if log_file.exists():
                    log_files.append(log_file)

            # Read events from files
            for log_file in log_files:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            try:
                                event_data = json.loads(line)
                                event = SecurityEvent(
                                    event_type=SecurityEventType(event_data['event_type']),
                                    timestamp=datetime.fromisoformat(event_data['timestamp']),
                                    container_id=event_data['container_id'],
                                    language=event_data['language'],
                                    code_hash=event_data['code_hash'],
                                    details=event_data['details'],
                                    severity=event_data.get('severity', 'info')
                                )

                                # Apply filters
                                if event_type and event.event_type != event_type:
                                    continue
                                if container_id and event.container_id != container_id:
                                    continue
                                if start_date and event.timestamp < start_date:
                                    continue
                                if end_date and event.timestamp > end_date:
                                    continue

                                events.append(event)
                            except (json.JSONDecodeError, KeyError, ValueError) as e:
                                logger.warning(f"Invalid log entry: {e}")
                                continue

        except Exception as e:
            logger.error(f"Error retrieving audit events: {e}")

        return events


class CodeAnalyzer:
    """Analyzes code for security risks."""

    # Patterns that indicate potentially dangerous operations
    SHELL_PATTERNS = [
        r'\b(?:exec|system|popen|subprocess|os\.system|os\.popen)\b',
        r'\b(?:sh|bash|zsh|cmd|powershell)\b.*(?:-c|--command)',
        r'\$\(.*\)',  # Command substitution in shell
    ]

    NETWORK_PATTERNS = [
        r'\b(?:socket|requests|urllib|http|ftp|tcp|udp)\b',
        r'\b(?:connect|bind|listen|accept)\b',
        r'\b(?:127\.0\.0\.1|localhost|0\.0\.0\.0)\b',
    ]

    FILESYSTEM_PATTERNS = [
        r'\b(?:open|read|write|chmod|chown|unlink|mkdir|rmdir)\b',
        r'\b(?:/etc|/proc|/sys|/dev)\b',  # System directories
        r'\.\.',  # Directory traversal
    ]

    SYSTEM_PATTERNS = [
        r'\b(?:fork|kill|signal|ptrace|setuid|setgid)\b',
        r'\b(?:import os|import sys)\b.*(?:system|exec)',
    ]

    MALICIOUS_PATTERNS = [
        r'\b(?:eval|exec)\s*\(',
        r'\b__import__\s*\(',
        r'\bglobals\(\)|locals\(\)',
        r'\bgetattr\s*\(\s*.*\s*,\s*.*\)\s*=',
    ]

    def __init__(self):
        self.patterns = {
            'shell': self.SHELL_PATTERNS,
            'network': self.NETWORK_PATTERNS,
            'filesystem': self.FILESYSTEM_PATTERNS,
            'system': self.SYSTEM_PATTERNS,
            'malicious': self.MALICIOUS_PATTERNS,
        }

    def analyze_code(self, code: str, language: str) -> CodeAnalysis:
        """Analyze code for security risks."""
        analysis = CodeAnalysis()
        code_lower = code.lower()

        # Check for various patterns
        analysis.has_shell_commands = self._check_patterns(code, self.SHELL_PATTERNS)
        analysis.has_network_calls = self._check_patterns(code, self.NETWORK_PATTERNS)
        analysis.has_file_operations = self._check_patterns(code, self.FILESYSTEM_PATTERNS)
        analysis.has_system_calls = self._check_patterns(code, self.SYSTEM_PATTERNS)

        # Check for imports (language-specific)
        analysis.has_imports = self._check_imports(code, language)

        # Find suspicious patterns
        for category, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, code, re.IGNORECASE)
                if matches:
                    analysis.suspicious_patterns.extend(matches)

        # Calculate risk score
        analysis.risk_score = self._calculate_risk_score(analysis)

        return analysis

    def _check_patterns(self, code: str, patterns: List[str]) -> bool:
        """Check if code matches any of the given patterns."""
        for pattern in patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return True
        return False

    def _check_imports(self, code: str, language: str) -> bool:
        """Check for import statements based on language."""
        if language in ['python', 'python3']:
            return bool(re.search(r'^\s*(import|from)\s+', code, re.MULTILINE))
        elif language in ['javascript', 'typescript']:
            return bool(re.search(r'^\s*(import|require)\s*\(', code, re.MULTILINE))
        elif language == 'java':
            return bool(re.search(r'^\s*import\s+', code, re.MULTILINE))
        elif language in ['cpp', 'c']:
            return bool(re.search(r'^\s*#include\s+', code, re.MULTILINE))
        elif language == 'go':
            return bool(re.search(r'^\s*import\s+', code, re.MULTILINE))
        elif language == 'rust':
            return bool(re.search(r'^\s*use\s+', code, re.MULTILINE))
        return False

    def _calculate_risk_score(self, analysis: CodeAnalysis) -> int:
        """Calculate a risk score from 0-10."""
        score = 0

        if analysis.has_shell_commands:
            score += 3
        if analysis.has_network_calls:
            score += 2
        if analysis.has_file_operations:
            score += 2
        if analysis.has_system_calls:
            score += 3
        if analysis.has_imports:
            score += 1  # Imports themselves aren't necessarily risky

        score += min(len(analysis.suspicious_patterns), 3)  # Cap at 3 for suspicious patterns

        return min(score, 10)


class ProcessMonitor:
    """Monitors process behavior during execution."""

    def __init__(self):
        self.baseline_metrics = {}

    def get_process_info(self, pid: Optional[int] = None) -> Dict[str, Any]:
        """Get information about a process."""
        if not HAS_PSUTIL:
            return {'pid': pid or os.getpid(), 'psutil_unavailable': True}

        try:
            process = psutil.Process(pid or os.getpid())
            return {
                'pid': process.pid,
                'cpu_percent': process.cpu_percent(),
                'memory_info': process.memory_info()._asdict(),
                'num_threads': process.num_threads(),
                'num_fds': process.num_fds() if hasattr(process, 'num_fds') else None,
                'connections': len(process.connections()),
                'children': len(process.children(recursive=True)),
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.warning(f"Could not get process info: {e}")
            return {}

    def detect_anomalies(self, current_metrics: Dict[str, Any], baseline: Dict[str, Any]) -> List[str]:
        """Detect anomalous behavior based on metrics."""
        anomalies = []

        # Check CPU usage
        if current_metrics.get('cpu_percent', 0) > (baseline.get('cpu_percent', 0) * 2):
            anomalies.append("High CPU usage detected")

        # Check memory usage
        current_mem = current_metrics.get('memory_info', {}).get('rss', 0)
        baseline_mem = baseline.get('memory_info', {}).get('rss', 0)
        if current_mem > (baseline_mem * 3):  # 3x baseline
            anomalies.append("Excessive memory usage detected")

        # Check thread count
        if current_metrics.get('num_threads', 0) > (baseline.get('num_threads', 0) + 10):
            anomalies.append("High thread count detected")

        # Check connections
        if current_metrics.get('connections', 0) > 5:
            anomalies.append("Multiple network connections detected")

        # Check children processes
        if current_metrics.get('children', 0) > 5:
            anomalies.append("Multiple child processes detected")

        return anomalies


class SecurityUtils:
    """Main security utilities class."""

    def __init__(self, audit_log_dir: Optional[str] = None):
        self.audit_logger = AuditLogger(audit_log_dir)
        self.code_analyzer = CodeAnalyzer()
        self.process_monitor = ProcessMonitor()

    def analyze_and_log_execution(
        self,
        code: str,
        language: str,
        container_id: str,
        operation: str = "run"
    ) -> CodeAnalysis:
        """Analyze code and log the execution start."""
        # Analyze the code
        analysis = self.code_analyzer.analyze_code(code, language)

        # Generate code hash
        code_hash = hashlib.sha256(code.encode('utf-8')).hexdigest()[:16]

        # Log execution start
        start_event = SecurityEvent(
            event_type=SecurityEventType.CODE_EXECUTION_START,
            timestamp=datetime.now(),
            container_id=container_id,
            language=language,
            code_hash=code_hash,
            details={
                'operation': operation,
                'risk_score': analysis.risk_score,
                'has_shell_commands': analysis.has_shell_commands,
                'has_network_calls': analysis.has_network_calls,
                'suspicious_patterns_count': len(analysis.suspicious_patterns),
            },
            severity='warning' if analysis.risk_score > 5 else 'info'
        )
        self.audit_logger.log_event(start_event)

        return analysis

    def log_execution_result(
        self,
        container_id: str,
        language: str,
        code_hash: str,
        success: bool,
        execution_time: float,
        exit_code: int,
        anomalies: Optional[List[str]] = None
    ) -> None:
        """Log the execution result."""
        severity = 'error' if not success or anomalies else 'info'

        if anomalies:
            severity = 'warning' if any('detected' in anomaly.lower() for anomaly in anomalies) else 'info'

        end_event = SecurityEvent(
            event_type=SecurityEventType.CODE_EXECUTION_END,
            timestamp=datetime.now(),
            container_id=container_id,
            language=language,
            code_hash=code_hash,
            details={
                'success': success,
                'execution_time': execution_time,
                'exit_code': exit_code,
                'anomalies': anomalies or [],
            },
            severity=severity
        )
        self.audit_logger.log_event(end_event)

    def log_anomaly(
        self,
        container_id: str,
        language: str,
        anomaly_type: str,
        details: Dict[str, Any]
    ) -> None:
        """Log a security anomaly."""
        event = SecurityEvent(
            event_type=SecurityEventType.CONTAINER_ANOMALY,
            timestamp=datetime.now(),
            container_id=container_id,
            language=language,
            code_hash="",  # May not have code hash for anomalies
            details=details,
            severity='warning'
        )
        self.audit_logger.log_event(event)

    def get_audit_events(self, **kwargs) -> List[SecurityEvent]:
        """Get audit events with filtering."""
        return self.audit_logger.get_events(**kwargs)

    def hash_code(self, code: str) -> str:
        """Generate a hash for code content."""
        return hashlib.sha256(code.encode('utf-8')).hexdigest()[:16]