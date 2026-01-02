# Copyright 2025 tbaur
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

"""
Metrics collection and reporting for playlist-builder operations.
"""
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from collections import defaultdict

from constants import BOLD, GREEN, YELLOW, CYAN, BLUE, MAGENTA, RED, RESET, DIM

@dataclass
class OperationMetrics:
    """Metrics for a single operation."""
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    success: bool = False
    error_message: Optional[str] = None
    items_processed: int = 0
    items_succeeded: int = 0
    items_failed: int = 0
    additional_stats: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        """Get operation duration in seconds."""
        if self.end_time:
            return self.end_time - self.start_time
        return time.perf_counter() - self.start_time
    
    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        total = self.items_processed
        if total == 0:
            return 100.0 if self.success else 0.0
        return (self.items_succeeded / total) * 100.0

class MetricsCollector:
    """Collects and reports metrics for operations."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.operations: List[OperationMetrics] = []
        self.current_operation: Optional[OperationMetrics] = None
    
    def start_operation(self, name: str) -> OperationMetrics:
        """
        Start tracking an operation.
        
        Args:
            name: Operation name
            
        Returns:
            OperationMetrics instance
        """
        metrics = OperationMetrics(
            operation_name=name,
            start_time=time.perf_counter()
        )
        self.current_operation = metrics
        self.operations.append(metrics)
        return metrics
    
    def end_operation(self, success: bool = True, error: Optional[str] = None):
        """
        End the current operation.
        
        Args:
            success: Whether operation succeeded
            error: Error message if failed
        """
        if self.current_operation:
            self.current_operation.end_time = time.perf_counter()
            self.current_operation.success = success
            self.current_operation.error_message = error
            self.current_operation = None
    
    def update_items(self, processed: int = 0, succeeded: int = 0, failed: int = 0):
        """
        Update item counts for current operation.
        
        Args:
            processed: Total items processed
            succeeded: Items that succeeded
            failed: Items that failed
        """
        if self.current_operation:
            self.current_operation.items_processed = processed
            self.current_operation.items_succeeded = succeeded
            self.current_operation.items_failed = failed
    
    def add_stat(self, key: str, value: any):
        """
        Add additional statistic to current operation.
        
        Args:
            key: Statistic key
            value: Statistic value
        """
        if self.current_operation:
            self.current_operation.additional_stats[key] = value
    
    def get_total_duration(self) -> float:
        """Get total duration of all operations."""
        return sum(op.duration for op in self.operations)
    
    def print_summary(self):
        """Print comprehensive metrics summary."""
        if not self.operations:
            return
        
        total_duration = self.get_total_duration()
        
        print(f"\n{BLUE}{'━'*120}{RESET}")
        print(f"{BOLD}{CYAN}METRICS & HEALTH REPORT{RESET}")
        print(f"{BLUE}{'━'*120}{RESET}\n")
        
        # Overall summary
        print(f"{BOLD}OVERALL PERFORMANCE:{RESET}")
        total_ops = len(self.operations)
        successful_ops = sum(1 for op in self.operations if op.success)
        print(f"  Operations: {CYAN}{total_ops}{RESET} total, {GREEN}{successful_ops}{RESET} successful, {RED if total_ops - successful_ops > 0 else YELLOW}{total_ops - successful_ops}{RESET} failed")
        print(f"  Total Duration: {CYAN}{total_duration:.2f}s{RESET}")
        print(f"  Average Operation Time: {CYAN}{total_duration / total_ops:.2f}s{RESET}\n")
        
        # Per-operation details
        print(f"{BOLD}OPERATION BREAKDOWN:{RESET}")
        for op in self.operations:
            status_icon = f"{GREEN}✓{RESET}" if op.success else f"{RED}✗{RESET}"
            status_text = f"{GREEN}SUCCESS{RESET}" if op.success else f"{RED}FAILED{RESET}"
            
            print(f"\n  {status_icon} {BOLD}{op.operation_name}{RESET} - {status_text}")
            print(f"    Duration: {CYAN}{op.duration:.3f}s{RESET}")
            
            if op.items_processed > 0:
                success_rate = op.success_rate
                rate_color = GREEN if success_rate >= 90 else YELLOW if success_rate >= 70 else RED
                print(f"    Items: {CYAN}{op.items_processed}{RESET} processed, {GREEN}{op.items_succeeded}{RESET} succeeded, {RED}{op.items_failed}{RESET} failed")
                print(f"    Success Rate: {rate_color}{success_rate:.1f}%{RESET}")
            
            if op.additional_stats:
                print(f"    {DIM}Additional Stats:{RESET}")
                for key, value in op.additional_stats.items():
                    if isinstance(value, (int, float)):
                        if isinstance(value, float):
                            print(f"      {key}: {CYAN}{value:.2f}{RESET}")
                        else:
                            print(f"      {key}: {CYAN}{value}{RESET}")
                    else:
                        print(f"      {key}: {CYAN}{value}{RESET}")
            
            if op.error_message:
                print(f"    {RED}Error: {op.error_message}{RESET}")
        
        # Health status
        print(f"\n{BOLD}HEALTH STATUS:{RESET}")
        all_successful = all(op.success for op in self.operations)
        high_success_rate = all(
            op.success_rate >= 90 or op.items_processed == 0 
            for op in self.operations 
            if op.items_processed > 0
        )
        
        if all_successful and high_success_rate:
            health_status = f"{GREEN}HEALTHY{RESET}"
            health_desc = "All operations completed successfully with high success rates."
        elif all_successful:
            health_status = f"{YELLOW}DEGRADED{RESET}"
            health_desc = "Operations completed but some had lower success rates."
        else:
            health_status = f"{RED}UNHEALTHY{RESET}"
            health_desc = "Some operations failed. Review errors above."
        
        print(f"  Status: {health_status}")
        print(f"  {DIM}{health_desc}{RESET}")
        
        print(f"\n{BLUE}{'━'*120}{RESET}\n")

