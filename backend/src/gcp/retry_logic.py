"""
Retry Logic for GCP Marketplace Webhooks
Implements exponential backoff for failed webhook operations
"""

import asyncio
import logging
import random
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryConfig:
    """Configuration for retry behavior"""

    def __init__(
        self,
        max_attempts: int = 5,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """
        Initialize retry configuration

        Args:
            max_attempts: Maximum number of retry attempts
            initial_delay: Initial delay in seconds before first retry
            max_delay: Maximum delay in seconds between retries
            exponential_base: Base for exponential backoff calculation
            jitter: Add random jitter to prevent thundering herd
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt number

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        # Exponential backoff: delay = initial_delay * (base ^ attempt)
        delay = self.initial_delay * (self.exponential_base**attempt)

        # Cap at max_delay
        delay = min(delay, self.max_delay)

        # Add jitter if enabled (random between 0 and delay)
        if self.jitter:
            delay = random.uniform(0, delay)

        return delay


# Default configurations for different operations
DEFAULT_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    initial_delay=1.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True,
)

WEBHOOK_RETRY_CONFIG = RetryConfig(
    max_attempts=3,  # Webhooks should fail fast
    initial_delay=0.5,
    max_delay=10.0,
    exponential_base=2.0,
    jitter=True,
)

USAGE_REPORT_RETRY_CONFIG = RetryConfig(
    max_attempts=7,  # Usage reporting is critical
    initial_delay=2.0,
    max_delay=120.0,
    exponential_base=2.0,
    jitter=True,
)


class RetryableError(Exception):
    """
    Exception that indicates an operation should be retried
    """

    pass


class NonRetryableError(Exception):
    """
    Exception that indicates an operation should NOT be retried
    """

    pass


async def retry_async(
    func: Callable[..., Any],
    *args,
    config: Optional[RetryConfig] = None,
    retry_on: tuple = (Exception,),
    dont_retry_on: tuple = (NonRetryableError,),
    **kwargs,
) -> Any:
    """
    Retry an async function with exponential backoff

    Args:
        func: Async function to retry
        *args: Positional arguments for func
        config: Retry configuration (uses DEFAULT_RETRY_CONFIG if None)
        retry_on: Tuple of exceptions to retry on
        dont_retry_on: Tuple of exceptions to NOT retry on
        **kwargs: Keyword arguments for func

    Returns:
        Result of successful function call

    Raises:
        Last exception if all retries fail

    Example:
        result = await retry_async(
            gcp_client.report_usage,
            entitlement_id="ent_123",
            metrics={"calls": 100},
            config=USAGE_REPORT_RETRY_CONFIG
        )
    """
    if config is None:
        config = DEFAULT_RETRY_CONFIG

    last_exception = None

    for attempt in range(config.max_attempts):
        try:
            # Attempt the operation
            result = await func(*args, **kwargs)

            # Success! Log if we had previous failures
            if attempt > 0:
                logger.info(f"{func.__name__} succeeded after {attempt + 1} attempts")

            return result

        except dont_retry_on as e:
            # Non-retryable error - fail immediately
            logger.error(
                f"{func.__name__} failed with non-retryable error: {e}", exc_info=True
            )
            raise

        except retry_on as e:
            last_exception = e

            # Check if we have more attempts
            if attempt < config.max_attempts - 1:
                # Calculate delay
                delay = config.calculate_delay(attempt)

                logger.warning(
                    f"{func.__name__} failed (attempt {attempt + 1}/{config.max_attempts}): {e}. "
                    f"Retrying in {delay:.2f} seconds..."
                )

                # Wait before retrying
                await asyncio.sleep(delay)
            else:
                # Last attempt failed
                logger.error(
                    f"{func.__name__} failed after {config.max_attempts} attempts: {e}",
                    exc_info=True,
                )

    # All retries exhausted
    raise last_exception


def with_retry(
    config: Optional[RetryConfig] = None,
    retry_on: tuple = (Exception,),
    dont_retry_on: tuple = (NonRetryableError,),
):
    """
    Decorator to add retry logic to async functions

    Args:
        config: Retry configuration
        retry_on: Tuple of exceptions to retry on
        dont_retry_on: Tuple of exceptions to NOT retry on

    Example:
        @with_retry(config=WEBHOOK_RETRY_CONFIG)
        async def process_webhook(data):
            # This function will be retried on failure
            return await some_operation(data)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_async(
                func,
                *args,
                config=config,
                retry_on=retry_on,
                dont_retry_on=dont_retry_on,
                **kwargs,
            )

        return wrapper

    return decorator


# Specific retry decorators for common operations
def with_webhook_retry(func: Callable) -> Callable:
    """
    Decorator for webhook operations (fast fail)
    """
    return with_retry(config=WEBHOOK_RETRY_CONFIG)(func)


def with_usage_report_retry(func: Callable) -> Callable:
    """
    Decorator for usage reporting operations (persistent)
    """
    return with_retry(config=USAGE_REPORT_RETRY_CONFIG)(func)


# Circuit breaker pattern (advanced retry logic)
class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail immediately
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception,
    ):
        """
        Initialize circuit breaker

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying again (half-open)
            expected_exception: Exception type that counts as failure
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def __call__(self, func: Callable) -> Callable:
        """
        Decorator to apply circuit breaker
        """

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Check circuit state
            if self.state == "OPEN":
                # Check if recovery timeout has passed
                import time

                if time.time() - self.last_failure_time >= self.recovery_timeout:
                    logger.info(
                        f"Circuit breaker for {func.__name__} entering HALF_OPEN state"
                    )
                    self.state = "HALF_OPEN"
                else:
                    # Still in open state - fail fast
                    raise NonRetryableError(
                        f"Circuit breaker OPEN for {func.__name__}. "
                        f"Failures: {self.failure_count}/{self.failure_threshold}"
                    )

            try:
                # Attempt operation
                result = await func(*args, **kwargs)

                # Success! Reset circuit if it was half-open
                if self.state == "HALF_OPEN":
                    logger.info(
                        f"Circuit breaker for {func.__name__} closing (recovered)"
                    )
                    self.state = "CLOSED"
                    self.failure_count = 0

                return result

            except self.expected_exception as e:
                # Operation failed
                self.failure_count += 1
                import time

                self.last_failure_time = time.time()

                logger.warning(
                    f"Circuit breaker for {func.__name__}: "
                    f"failure {self.failure_count}/{self.failure_threshold}"
                )

                # Check if we should open circuit
                if self.failure_count >= self.failure_threshold:
                    self.state = "OPEN"
                    logger.error(
                        f"Circuit breaker OPENED for {func.__name__} "
                        f"after {self.failure_count} failures"
                    )

                raise

        return wrapper


# Example usage:
# @CircuitBreaker(failure_threshold=5, recovery_timeout=60)
# @with_retry(config=USAGE_REPORT_RETRY_CONFIG)
# async def report_usage_to_gcp(entitlement_id, metrics):
#     # This will retry with backoff, and open circuit after 5 failures
#     return await gcp_client.report_usage(entitlement_id, metrics)
