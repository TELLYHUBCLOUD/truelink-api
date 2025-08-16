import time
import psutil
import logging
from typing import Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class HealthMetrics:
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    active_connections: int
    response_time_avg: float
    error_rate: float
    timestamp: datetime

class HealthMonitor:
    def __init__(self):
        self.metrics_history = []
        self.error_count = 0
        self.request_count = 0
        self.response_times = []
        
    def record_request(self, response_time: float, is_error: bool = False):
        """Record request metrics"""
        self.request_count += 1
        self.response_times.append(response_time)
        
        if is_error:
            self.error_count += 1
            
        # Keep only last 1000 response times
        if len(self.response_times) > 1000:
            self.response_times = self.response_times[-1000:]
    
    def get_current_metrics(self) -> HealthMetrics:
        """Get current system health metrics"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Network connections (approximate)
        connections = len(psutil.net_connections())
        
        # Calculate averages
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        error_rate = (self.error_count / self.request_count) if self.request_count > 0 else 0
        
        return HealthMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            disk_usage_percent=(disk.used / disk.total) * 100,
            active_connections=connections,
            response_time_avg=avg_response_time,
            error_rate=error_rate,
            timestamp=datetime.utcnow()
        )
    
    def check_alerts(self, metrics: HealthMetrics) -> List[str]:
        """Check for alert conditions"""
        alerts = []
        
        if metrics.cpu_percent > 80:
            alerts.append(f"High CPU usage: {metrics.cpu_percent:.1f}%")
            
        if metrics.memory_percent > 85:
            alerts.append(f"High memory usage: {metrics.memory_percent:.1f}%")
            
        if metrics.error_rate > 0.05:  # 5% error rate
            alerts.append(f"High error rate: {metrics.error_rate:.2%}")
            
        if metrics.response_time_avg > 5.0:  # 5 second average
            alerts.append(f"Slow response times: {metrics.response_time_avg:.2f}s")
            
        return alerts

# Global monitor instance
health_monitor = HealthMonitor()