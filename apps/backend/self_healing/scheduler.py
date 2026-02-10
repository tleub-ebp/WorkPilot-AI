"""
Health Check Scheduler
======================

Schedules periodic health checks and auto-healing runs.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, time
from pathlib import Path
from typing import Optional

try:
    from debug import debug, debug_section, debug_success
except ImportError:
    def debug(module: str, message: str, **kwargs): pass
    def debug_section(module: str, message: str): pass
    def debug_success(module: str, message: str, **kwargs): pass

from .config import HealingConfig, MonitoringFrequency
from .monitor import SelfHealingMonitor


class HealthCheckScheduler:
    """Schedules periodic health checks."""
    
    def __init__(
        self,
        project_dir: str | Path,
        config: Optional[HealingConfig] = None,
    ):
        self.project_dir = Path(project_dir)
        self.config = config or HealingConfig()
        self.monitor = SelfHealingMonitor(project_dir, config)
        
        self.running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start_monitoring(self) -> None:
        """Start periodic monitoring."""
        debug_section("scheduler", "🕐 Starting Health Monitoring")
        
        if not self.config.monitoring_enabled:
            debug("self_healing", "Monitoring is disabled")
            return
        
        self.running = True
        self._task = asyncio.create_task(self._monitoring_loop())
        
        debug_success("scheduler", "Health monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop monitoring."""
        debug("self_healing", "Stopping health monitoring")
        
        self.running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.running:
            try:
                # Run health check
                await self.monitor.run_health_check()
                
                # Run auto-heal if configured
                if self.config.auto_fix_enabled:
                    # Check if we're in night hours for intensive ops
                    if self._is_night_time() or not self.config.schedule_night_runs:
                        await self.monitor.auto_heal()
                
                # Wait for next check
                sleep_seconds = self._get_sleep_duration()
                await asyncio.sleep(sleep_seconds)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                debug("self_healing", f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait a bit on error
    
    def _get_sleep_duration(self) -> int:
        """Get sleep duration based on frequency."""
        frequency_map = {
            MonitoringFrequency.REALTIME: 0,  # No sleep, run continuously
            MonitoringFrequency.HOURLY: 3600,  # 1 hour
            MonitoringFrequency.DAILY: 86400,  # 24 hours
            MonitoringFrequency.WEEKLY: 604800,  # 7 days
        }
        
        return frequency_map.get(self.config.frequency, 86400)
    
    def _is_night_time(self) -> bool:
        """Check if current time is in night window."""
        if not self.config.schedule_night_runs:
            return False
        
        now = datetime.now().time()
        night_start = time(hour=self.config.night_start_hour)
        night_end = time(hour=self.config.night_end_hour)
        
        if night_start > night_end:
            # Spans midnight
            return now >= night_start or now < night_end
        else:
            return night_start <= now < night_end
    
    async def run_once(self) -> None:
        """Run health check and auto-heal once."""
        debug_section("scheduler", "🧬 Running One-Time Health Check")
        
        await self.monitor.run_health_check()
        
        if self.config.auto_fix_enabled:
            await self.monitor.auto_heal()