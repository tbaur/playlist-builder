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
Tests for metrics module.
"""
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metrics import MetricsCollector, OperationMetrics
from constants import GREEN, RED, YELLOW


class TestOperationMetrics:
    """Test OperationMetrics dataclass."""
    
    def test_init(self):
        """Test OperationMetrics initialization."""
        start_time = time.perf_counter()
        metrics = OperationMetrics(
            operation_name="test_op",
            start_time=start_time
        )
        
        assert metrics.operation_name == "test_op"
        assert metrics.start_time == start_time
        assert metrics.end_time is None
        assert metrics.success is False
        assert metrics.items_processed == 0
        assert metrics.items_succeeded == 0
        assert metrics.items_failed == 0
    
    def test_duration_without_end_time(self):
        """Test duration property when end_time not set."""
        start_time = time.perf_counter()
        metrics = OperationMetrics(
            operation_name="test",
            start_time=start_time
        )
        
        duration = metrics.duration
        assert duration >= 0
        assert isinstance(duration, float)
    
    def test_duration_with_end_time(self):
        """Test duration property with end_time set."""
        start_time = time.perf_counter()
        time.sleep(0.01)
        end_time = time.perf_counter()
        
        metrics = OperationMetrics(
            operation_name="test",
            start_time=start_time,
            end_time=end_time
        )
        
        duration = metrics.duration
        assert duration > 0
        assert duration == (end_time - start_time)
    
    def test_success_rate_no_items(self):
        """Test success rate with no items processed."""
        metrics = OperationMetrics(
            operation_name="test",
            start_time=time.perf_counter(),
            success=True
        )
        
        assert metrics.success_rate == 100.0
    
    def test_success_rate_all_succeeded(self):
        """Test success rate when all items succeeded."""
        metrics = OperationMetrics(
            operation_name="test",
            start_time=time.perf_counter(),
            items_processed=10,
            items_succeeded=10,
            items_failed=0
        )
        
        assert metrics.success_rate == 100.0
    
    def test_success_rate_partial_success(self):
        """Test success rate with partial success."""
        metrics = OperationMetrics(
            operation_name="test",
            start_time=time.perf_counter(),
            items_processed=10,
            items_succeeded=7,
            items_failed=3
        )
        
        assert metrics.success_rate == 70.0
    
    def test_success_rate_all_failed(self):
        """Test success rate when all items failed."""
        metrics = OperationMetrics(
            operation_name="test",
            start_time=time.perf_counter(),
            items_processed=10,
            items_succeeded=0,
            items_failed=10,
            success=False
        )
        
        assert metrics.success_rate == 0.0
    
    def test_additional_stats(self):
        """Test additional statistics."""
        metrics = OperationMetrics(
            operation_name="test",
            start_time=time.perf_counter()
        )
        
        metrics.additional_stats["test_key"] = "test_value"
        assert metrics.additional_stats["test_key"] == "test_value"


class TestMetricsCollector:
    """Test MetricsCollector class."""
    
    def test_init(self):
        """Test MetricsCollector initialization."""
        collector = MetricsCollector()
        
        assert len(collector.operations) == 0
        assert collector.current_operation is None
    
    def test_start_operation(self):
        """Test starting an operation."""
        collector = MetricsCollector()
        metrics = collector.start_operation("test_op")
        
        assert isinstance(metrics, OperationMetrics)
        assert metrics.operation_name == "test_op"
        assert len(collector.operations) == 1
        assert collector.current_operation == metrics
    
    def test_end_operation(self):
        """Test ending an operation."""
        collector = MetricsCollector()
        collector.start_operation("test_op")
        
        collector.end_operation(success=True)
        
        assert collector.operations[0].success is True
        assert collector.operations[0].end_time is not None
        assert collector.current_operation is None
    
    def test_end_operation_with_error(self):
        """Test ending operation with error."""
        collector = MetricsCollector()
        collector.start_operation("test_op")
        
        collector.end_operation(success=False, error="Test error")
        
        assert collector.operations[0].success is False
        assert collector.operations[0].error_message == "Test error"
    
    def test_update_items(self):
        """Test updating item counts."""
        collector = MetricsCollector()
        collector.start_operation("test_op")
        
        collector.update_items(processed=10, succeeded=8, failed=2)
        
        assert collector.operations[0].items_processed == 10
        assert collector.operations[0].items_succeeded == 8
        assert collector.operations[0].items_failed == 2
    
    def test_update_items_no_current_operation(self):
        """Test updating items when no current operation."""
        collector = MetricsCollector()
        
        # Should not raise error
        collector.update_items(processed=10, succeeded=8, failed=2)
        
        assert len(collector.operations) == 0
    
    def test_add_stat(self):
        """Test adding additional statistics."""
        collector = MetricsCollector()
        collector.start_operation("test_op")
        
        collector.add_stat("avg_latency", 150.5)
        collector.add_stat("hi_res_count", 5)
        
        assert collector.operations[0].additional_stats["avg_latency"] == 150.5
        assert collector.operations[0].additional_stats["hi_res_count"] == 5
    
    def test_add_stat_no_current_operation(self):
        """Test adding stat when no current operation."""
        collector = MetricsCollector()
        
        # Should not raise error
        collector.add_stat("test", "value")
    
    def test_get_total_duration(self):
        """Test getting total duration."""
        collector = MetricsCollector()
        
        # No operations
        assert collector.get_total_duration() == 0.0
        
        # Single operation
        collector.start_operation("op1")
        time.sleep(0.01)
        collector.end_operation()
        
        duration = collector.get_total_duration()
        assert duration > 0
        
        # Multiple operations
        collector.start_operation("op2")
        time.sleep(0.01)
        collector.end_operation()
        
        total_duration = collector.get_total_duration()
        assert total_duration > duration
    
    def test_multiple_operations(self):
        """Test tracking multiple operations."""
        collector = MetricsCollector()
        
        collector.start_operation("op1")
        collector.end_operation(success=True)
        
        collector.start_operation("op2")
        collector.end_operation(success=False, error="Failed")
        
        assert len(collector.operations) == 2
        assert collector.operations[0].operation_name == "op1"
        assert collector.operations[1].operation_name == "op2"
        assert collector.operations[0].success is True
        assert collector.operations[1].success is False
    
    def test_print_summary_empty(self, capsys):
        """Test printing summary with no operations."""
        collector = MetricsCollector()
        collector.print_summary()
        
        captured = capsys.readouterr()
        assert captured.out == ""
    
    def test_print_summary_single_operation(self, capsys):
        """Test printing summary with single operation."""
        collector = MetricsCollector()
        collector.start_operation("test_op")
        collector.update_items(processed=10, succeeded=9, failed=1)
        collector.add_stat("avg_latency", 150.5)
        collector.end_operation(success=True)
        
        collector.print_summary()
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "METRICS & HEALTH REPORT" in output
        assert "test_op" in output
        assert "SUCCESS" in output
        assert "10" in output
        assert "9" in output
        assert "1" in output
        assert "avg_latency" in output
    
    def test_print_summary_failed_operation(self, capsys):
        """Test printing summary with failed operation."""
        collector = MetricsCollector()
        collector.start_operation("failed_op")
        collector.end_operation(success=False, error="Test error")
        
        collector.print_summary()
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "FAILED" in output
        assert "Test error" in output
        assert "UNHEALTHY" in output
    
    def test_print_summary_health_status_healthy(self, capsys):
        """Test health status shows HEALTHY."""
        collector = MetricsCollector()
        collector.start_operation("op1")
        collector.update_items(processed=10, succeeded=10, failed=0)
        collector.end_operation(success=True)
        
        collector.print_summary()
        
        captured = capsys.readouterr()
        assert "HEALTHY" in captured.out
    
    def test_print_summary_with_items_processed(self, capsys):
        """Test printing summary with items processed (covers lines 149-151)."""
        collector = MetricsCollector()
        op = collector.start_operation("Test Op")
        collector.update_items(processed=100, succeeded=95, failed=5)
        collector.end_operation(success=True)
        
        collector.print_summary()
        captured = capsys.readouterr()
        output = captured.out
        
        # Should show items processed, succeeded, failed, and success rate
        assert "100" in output or "processed" in output.lower()
        assert "95" in output or "succeeded" in output.lower()
        assert "5" in output or "failed" in output.lower()
        assert "Success Rate" in output or "success rate" in output.lower()
    
    def test_print_summary_health_status_degraded(self, capsys):
        """Test health status shows DEGRADED."""
        collector = MetricsCollector()
        collector.start_operation("op1")
        collector.update_items(processed=10, succeeded=7, failed=3)  # 70% success
        collector.end_operation(success=True)
        
        collector.print_summary()
        
        captured = capsys.readouterr()
        assert "DEGRADED" in captured.out
    
    def test_print_summary_health_status_unhealthy(self, capsys):
        """Test health status shows UNHEALTHY."""
        collector = MetricsCollector()
        collector.start_operation("op1")
        collector.end_operation(success=False, error="Failed")
        
        collector.print_summary()
        
        captured = capsys.readouterr()
        assert "UNHEALTHY" in captured.out

