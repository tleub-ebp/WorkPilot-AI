#!/usr/bin/env python3
"""
Distributed Skills System

Manages skills distributed across multiple services and locations
with load balancing, failover, and remote execution capabilities.

Features:
- Remote skill execution
- Load balancing across services
- Failover and redundancy
- Service discovery
- Health monitoring
- Distributed caching
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Status of distributed services."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ExecutionLocation(Enum):
    """Where skills should be executed."""

    LOCAL = "local"
    REMOTE = "remote"
    AUTO = "auto"


@dataclass
class ServiceEndpoint:
    """Represents a remote service endpoint."""

    service_id: str
    name: str
    url: str
    location: str
    skills: set[str] = field(default_factory=set)
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_check: float = field(default_factory=time.time)
    response_time: float = 0.0
    error_rate: float = 0.0
    request_count: int = 0
    max_concurrent_requests: int = 10
    current_requests: int = 0

    def __post_init__(self):
        self.lock = threading.Lock()

    def is_available(self) -> bool:
        """Check if service is available for requests."""
        with self.lock:
            return (
                self.status == ServiceStatus.HEALTHY
                and self.current_requests < self.max_concurrent_requests
                and self.error_rate < 0.5  # Less than 50% error rate
            )

    def update_status(self, status: ServiceStatus, response_time: float = 0.0):
        """Update service status."""
        with self.lock:
            self.status = status
            self.last_check = time.time()
            self.response_time = response_time

    def increment_request(self):
        """Increment request counter."""
        with self.lock:
            self.request_count += 1
            self.current_requests += 1

    def decrement_request(self, success: bool = True):
        """Decrement request counter and update error rate."""
        with self.lock:
            self.current_requests = max(0, self.current_requests - 1)

            # Update error rate with exponential moving average
            if not success:
                self.error_rate = min(1.0, self.error_rate * 0.9 + 0.1)
            else:
                self.error_rate = max(0.0, self.error_rate * 0.9)


@dataclass
class RemoteSkillRequest:
    """Request for remote skill execution."""

    skill_name: str
    method: str
    parameters: dict[str, Any]
    context: dict[str, Any]
    timeout: float = 30.0
    retry_attempts: int = 2


@dataclass
class RemoteSkillResponse:
    """Response from remote skill execution."""

    success: bool
    result: Any | None = None
    error: str | None = None
    execution_time: float = 0.0
    service_id: str
    tokens_used: int = 0


class ServiceHealthChecker:
    """Monitors health of distributed services."""

    def __init__(self, check_interval: float = 30.0):
        self.check_interval = check_interval
        self.endpoints: dict[str, ServiceEndpoint] = {}
        self.running = False
        self.check_thread = None

    def add_endpoint(self, endpoint: ServiceEndpoint):
        """Add a service endpoint for monitoring."""
        self.endpoints[endpoint.service_id] = endpoint
        logger.info(f"Added endpoint for monitoring: {endpoint.service_id}")

    def start_monitoring(self):
        """Start health monitoring."""
        if self.running:
            return

        self.running = True
        self.check_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.check_thread.start()
        logger.info("Started service health monitoring")

    def stop_monitoring(self):
        """Stop health monitoring."""
        self.running = False
        if self.check_thread:
            self.check_thread.join(timeout=5.0)
        logger.info("Stopped service health monitoring")

    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                self._check_all_endpoints()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                time.sleep(5.0)  # Brief delay before retry

    def _check_all_endpoints(self):
        """Check health of all endpoints."""
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self._check_endpoint, endpoint): endpoint.service_id
                for endpoint in self.endpoints.values()
            }

            for future in as_completed(futures):
                service_id = futures[future]
                try:
                    status, response_time = future.result()
                    endpoint = self.endpoints[service_id]
                    endpoint.update_status(status, response_time)
                except Exception as e:
                    logger.error(f"Health check failed for {service_id}: {e}")
                    if service_id in self.endpoints:
                        self.endpoints[service_id].update_status(
                            ServiceStatus.UNHEALTHY
                        )

    def _check_endpoint(self, endpoint: ServiceEndpoint) -> tuple[ServiceStatus, float]:
        """Check health of a single endpoint."""
        start_time = time.time()

        try:
            # Simple health check - try to reach the service
            health_url = urljoin(endpoint.url, "/health")
            response = requests.get(health_url, timeout=5.0)

            response_time = time.time() - start_time

            if response.status_code == 200:
                try:
                    health_data = response.json()
                    if health_data.get("status") == "healthy":
                        return ServiceStatus.HEALTHY, response_time
                    else:
                        return ServiceStatus.DEGRADED, response_time
                except Exception:
                    return (
                        ServiceStatus.HEALTHY,
                        response_time,
                    )  # Assume healthy if reachable
            else:
                return ServiceStatus.UNHEALTHY, response_time

        except requests.exceptions.Timeout:
            return ServiceStatus.UNHEALTHY, 5.0
        except requests.exceptions.ConnectionError:
            return ServiceStatus.UNHEALTHY, 5.0
        except Exception as e:
            logger.warning(f"Unexpected error checking {endpoint.service_id}: {e}")
            return ServiceStatus.UNKNOWN, time.time() - start_time


class DistributedSkillExecutor:
    """Executes skills on distributed services."""

    def __init__(self, local_skill_manager, health_checker: ServiceHealthChecker):
        self.local_skill_manager = local_skill_manager
        self.health_checker = health_checker
        self.request_timeout = 30.0
        self.max_retries = 2

        # Load balancing
        self.load_balancer = LoadBalancer()

        # Request tracking
        self.active_requests: dict[str, threading.Event] = {}
        self.request_results: dict[str, RemoteSkillResponse] = {}

    def execute_skill(
        self,
        request: RemoteSkillRequest,
        preferred_location: ExecutionLocation = ExecutionLocation.AUTO,
    ) -> RemoteSkillResponse:
        """Execute a skill on appropriate service."""
        # Determine execution location
        location = self._determine_execution_location(request, preferred_location)

        if location == ExecutionLocation.LOCAL:
            return self._execute_local(request)
        else:
            return self._execute_remote(request)

    def _determine_execution_location(
        self, request: RemoteSkillRequest, preferred: ExecutionLocation
    ) -> ExecutionLocation:
        """Determine where to execute the skill."""
        if preferred == ExecutionLocation.LOCAL:
            return ExecutionLocation.LOCAL

        if preferred == ExecutionLocation.REMOTE:
            return ExecutionLocation.REMOTE

        # Auto selection logic
        # Check if skill is available locally
        if self.local_skill_manager.get_skill_info(request.skill_name):
            # Check if remote services are available and healthier
            remote_endpoints = self._get_available_endpoints_for_skill(
                request.skill_name
            )
            if remote_endpoints:
                # Prefer remote if services are healthy and have lower latency
                avg_response_time = sum(
                    e.response_time for e in remote_endpoints
                ) / len(remote_endpoints)
                if avg_response_time < 1.0:  # Prefer remote if fast enough
                    return ExecutionLocation.REMOTE

        return ExecutionLocation.LOCAL

    def _execute_local(self, request: RemoteSkillRequest) -> RemoteSkillResponse:
        """Execute skill locally."""
        start_time = time.time()

        try:
            # Get skill from local manager
            skill = self.local_skill_manager.load_skill(request.skill_name)
            if not skill:
                return RemoteSkillResponse(
                    success=False,
                    error=f"Skill not found locally: {request.skill_name}",
                    execution_time=time.time() - start_time,
                    service_id="local",
                )

            # Execute skill method
            if hasattr(skill, request.method):
                method = getattr(skill, request.method)
                result = method(**request.parameters)

                return RemoteSkillResponse(
                    success=True,
                    result=result,
                    execution_time=time.time() - start_time,
                    service_id="local",
                )
            else:
                return RemoteSkillResponse(
                    success=False,
                    error=f"Method not found: {request.method}",
                    execution_time=time.time() - start_time,
                    service_id="local",
                )

        except Exception as e:
            return RemoteSkillResponse(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
                service_id="local",
            )

    def _execute_remote(self, request: RemoteSkillRequest) -> RemoteSkillResponse:
        """Execute skill on remote service."""
        # Select best endpoint
        endpoint = self.load_balancer.select_endpoint(
            self._get_available_endpoints_for_skill(request.skill_name)
        )

        if not endpoint:
            return RemoteSkillResponse(
                success=False,
                error="No available remote endpoints",
                execution_time=0.0,
                service_id="none",
            )

        # Execute remotely with retry logic
        for attempt in range(self.max_retries + 1):
            try:
                response = self._make_remote_request(endpoint, request)

                # Update endpoint statistics
                endpoint.increment_request()
                endpoint.decrement_request(response.success)

                return response

            except Exception as e:
                if attempt < self.max_retries:
                    logger.warning(
                        f"Remote execution failed (attempt {attempt + 1}), retrying: {e}"
                    )
                    time.sleep(1.0)  # Brief delay before retry
                    continue
                else:
                    endpoint.increment_request()
                    endpoint.decrement_request(False)

                    return RemoteSkillResponse(
                        success=False,
                        error=str(e),
                        execution_time=0.0,
                        service_id=endpoint.service_id,
                    )

    def _make_remote_request(
        self, endpoint: ServiceEndpoint, request: RemoteSkillRequest
    ) -> RemoteSkillResponse:
        """Make request to remote service."""
        start_time = time.time()

        url = urljoin(endpoint.url, f"/skills/{request.skill_name}/{request.method}")

        payload = {"parameters": request.parameters, "context": request.context}

        try:
            response = requests.post(
                url,
                json=payload,
                timeout=request.timeout,
                headers={"Content-Type": "application/json"},
            )

            execution_time = time.time() - start_time

            if response.status_code == 200:
                result_data = response.json()

                return RemoteSkillResponse(
                    success=result_data.get("success", False),
                    result=result_data.get("result"),
                    error=result_data.get("error"),
                    execution_time=execution_time,
                    service_id=endpoint.service_id,
                    tokens_used=result_data.get("tokens_used", 0),
                )
            else:
                return RemoteSkillResponse(
                    success=False,
                    error=f"HTTP {response.status_code}: {response.text}",
                    execution_time=execution_time,
                    service_id=endpoint.service_id,
                )

        except requests.exceptions.Timeout:
            return RemoteSkillResponse(
                success=False,
                error="Request timeout",
                execution_time=time.time() - start_time,
                service_id=endpoint.service_id,
            )
        except Exception as e:
            return RemoteSkillResponse(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
                service_id=endpoint.service_id,
            )

    def _get_available_endpoints_for_skill(
        self, skill_name: str
    ) -> list[ServiceEndpoint]:
        """Get available endpoints that can handle the skill."""
        available = []

        for endpoint in self.health_checker.endpoints.values():
            if endpoint.is_available() and skill_name in endpoint.skills:
                available.append(endpoint)

        return available


class LoadBalancer:
    """Load balancer for distributed services."""

    def __init__(self):
        self.strategies = {
            "round_robin": self._round_robin,
            "least_connections": self._least_connections,
            "response_time": self._response_time_based,
        }
        self.current_strategy = "least_connections"
        self.round_robin_index = 0

    def select_endpoint(
        self, endpoints: list[ServiceEndpoint]
    ) -> ServiceEndpoint | None:
        """Select best endpoint using current strategy."""
        if not endpoints:
            return None

        strategy_func = self.strategies.get(
            self.current_strategy, self._least_connections
        )
        return strategy_func(endpoints)

    def _round_robin(self, endpoints: list[ServiceEndpoint]) -> ServiceEndpoint:
        """Round-robin selection."""
        endpoint = endpoints[self.round_robin_index % len(endpoints)]
        self.round_robin_index += 1
        return endpoint

    def _least_connections(self, endpoints: list[ServiceEndpoint]) -> ServiceEndpoint:
        """Select endpoint with least connections."""
        return min(endpoints, key=lambda e: e.current_requests)

    def _response_time_based(self, endpoints: list[ServiceEndpoint]) -> ServiceEndpoint:
        """Select endpoint with best response time."""
        return min(endpoints, key=lambda e: e.response_time)

    def set_strategy(self, strategy: str):
        """Set load balancing strategy."""
        if strategy in self.strategies:
            self.current_strategy = strategy
            logger.info(f"Load balancing strategy changed to: {strategy}")
        else:
            logger.warning(f"Unknown load balancing strategy: {strategy}")


class DistributedSkillManager:
    """Main manager for distributed skills."""

    def __init__(self, local_skill_manager, config: dict | None = None):
        self.local_skill_manager = local_skill_manager
        self.config = config or {}

        # Components
        self.health_checker = ServiceHealthChecker(
            check_interval=self.config.get("health_check_interval", 30.0)
        )
        self.executor = DistributedSkillExecutor(
            local_skill_manager, self.health_checker
        )

        # Service registry
        self.service_registry: dict[str, ServiceEndpoint] = {}

        # Distributed cache
        self.distributed_cache = DistributedCache(
            ttl=self.config.get("cache_ttl", 300.0)
        )

        # Start monitoring
        self.health_checker.start_monitoring()

        logger.info("Distributed skill manager initialized")

    def register_service(
        self,
        service_id: str,
        name: str,
        url: str,
        location: str,
        skills: list[str],
        max_concurrent_requests: int = 10,
    ):
        """Register a remote service."""
        endpoint = ServiceEndpoint(
            service_id=service_id,
            name=name,
            url=url,
            location=location,
            skills=set(skills),
            max_concurrent_requests=max_concurrent_requests,
        )

        self.service_registry[service_id] = endpoint
        self.health_checker.add_endpoint(endpoint)

        logger.info(f"Registered remote service: {name} ({service_id})")

    def execute_skill(
        self,
        skill_name: str,
        method: str = "execute",
        parameters: dict | None = None,
        context: dict | None = None,
        location: ExecutionLocation = ExecutionLocation.AUTO,
    ) -> RemoteSkillResponse:
        """Execute a skill (local or remote)."""
        # Check cache first
        cache_key = f"{skill_name}:{method}:{hash(str(parameters))}"
        cached_result = self.distributed_cache.get(cache_key)
        if cached_result:
            logger.debug(f"Cache hit for {cache_key}")
            return cached_result

        # Create request
        request = RemoteSkillRequest(
            skill_name=skill_name,
            method=method,
            parameters=parameters or {},
            context=context or {},
            timeout=self.config.get("request_timeout", 30.0),
            retry_attempts=self.config.get("retry_attempts", 2),
        )

        # Execute
        result = self.executor.execute_skill(request, location)

        # Cache successful results
        if result.success:
            self.distributed_cache.set(cache_key, result)

        return result

    def get_service_status(self) -> dict[str, Any]:
        """Get status of all registered services."""
        status = {
            "total_services": len(self.service_registry),
            "healthy_services": 0,
            "degraded_services": 0,
            "unhealthy_services": 0,
            "services": {},
        }

        for service_id, endpoint in self.service_registry.items():
            status["services"][service_id] = {
                "name": endpoint.name,
                "location": endpoint.location,
                "status": endpoint.status.value,
                "response_time": endpoint.response_time,
                "error_rate": endpoint.error_rate,
                "current_requests": endpoint.current_requests,
                "max_requests": endpoint.max_concurrent_requests,
                "skills": list(endpoint.skills),
            }

            if endpoint.status == ServiceStatus.HEALTHY:
                status["healthy_services"] += 1
            elif endpoint.status == ServiceStatus.DEGRADED:
                status["degraded_services"] += 1
            else:
                status["unhealthy_services"] += 1

        return status

    def get_available_skills(self) -> set[str]:
        """Get all available skills (local + remote)."""
        skills = set()

        # Local skills
        local_skills = self.local_skill_manager.list_skills()
        skills.update(local_skills)

        # Remote skills
        for endpoint in self.service_registry.values():
            if endpoint.is_available():
                skills.update(endpoint.skills)

        return skills

    def set_load_balancing_strategy(self, strategy: str):
        """Set load balancing strategy."""
        self.executor.load_balancer.set_strategy(strategy)

    def get_performance_stats(self) -> dict[str, Any]:
        """Get performance statistics."""
        stats = {"cache_stats": self.distributed_cache.get_stats(), "service_stats": {}}

        for service_id, endpoint in self.service_registry.items():
            stats["service_stats"][service_id] = {
                "total_requests": endpoint.request_count,
                "error_rate": endpoint.error_rate,
                "avg_response_time": endpoint.response_time,
                "current_load": endpoint.current_requests
                / endpoint.max_concurrent_requests,
            }

        return stats

    def shutdown(self):
        """Shutdown the distributed manager."""
        self.health_checker.stop_monitoring()
        logger.info("Distributed skill manager shutdown")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


class DistributedCache:
    """Simple distributed cache implementation."""

    def __init__(self, ttl: float = 300.0):
        self.ttl = ttl
        self.cache: dict[str, tuple[Any, float]] = {}
        self.lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        """Get value from cache."""
        with self.lock:
            if key in self.cache:
                value, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    return value
                else:
                    del self.cache[key]
        return None

    def set(self, key: str, value: Any):
        """Set value in cache."""
        with self.lock:
            self.cache[key] = (value, time.time())

    def clear(self):
        """Clear all cache entries."""
        with self.lock:
            self.cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            current_time = time.time()
            valid_entries = sum(
                1
                for _, timestamp in self.cache.values()
                if current_time - timestamp < self.ttl
            )

            return {
                "total_entries": len(self.cache),
                "valid_entries": valid_entries,
                "expired_entries": len(self.cache) - valid_entries,
                "ttl": self.ttl,
            }
