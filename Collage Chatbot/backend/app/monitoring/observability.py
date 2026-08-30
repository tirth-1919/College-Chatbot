"""
Production Observability and Monitoring for AIT AI Assistant
Structured logging, metrics, error tracking, and performance monitoring
"""

import logging
import json
import time
import uuid
from typing import Optional, Dict, Any
from contextlib import contextmanager
from functools import wraps
from datetime import datetime
import os
from pathlib import Path

# Configure structured logging
class StructuredLogger:
    """
    Structured logger with context support
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup structured logging format"""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _log(self, level: str, message: str, **kwargs):
        """Structured log method"""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'message': message,
            **kwargs
        }
        self.logger.log(getattr(logging, level.upper()), json.dumps(log_data))
    
    def info(self, message: str, **kwargs):
        self._log('info', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log('warning', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log('error', message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self._log('debug', message, **kwargs)


class MetricsCollector:
    """
    Metrics collection for monitoring
    """
    
    def __init__(self):
        self.metrics = {
            'requests': {},
            'ai_calls': {},
            'rag_retrieval': {},
            'errors': {},
            'performance': {}
        }
    
    def increment_counter(self, metric_name: str, tags: Dict[str, str] = None):
        """Increment a counter metric"""
        if metric_name not in self.metrics['requests']:
            self.metrics['requests'][metric_name] = {'count': 0, 'tags': {}}
        
        self.metrics['requests'][metric_name]['count'] += 1
        if tags:
            self.metrics['requests'][metric_name]['tags'].update(tags)
    
    def record_timing(self, metric_name: str, duration_ms: float, tags: Dict[str, str] = None):
        """Record timing metric"""
        if metric_name not in self.metrics['performance']:
            self.metrics['performance'][metric_name] = {
                'count': 0,
                'total_ms': 0,
                'min_ms': float('inf'),
                'max_ms': 0,
                'tags': {}
            }
        
        metric = self.metrics['performance'][metric_name]
        metric['count'] += 1
        metric['total_ms'] += duration_ms
        metric['min_ms'] = min(metric['min_ms'], duration_ms)
        metric['max_ms'] = max(metric['max_ms'], duration_ms)
        
        if tags:
            metric['tags'].update(tags)
    
    def record_ai_call(self, provider: str, model: str, tokens: int, cost: float):
        """Record AI provider call metrics"""
        key = f"{provider}_{model}"
        if key not in self.metrics['ai_calls']:
            self.metrics['ai_calls'][key] = {
                'calls': 0,
                'tokens': 0,
                'cost': 0.0
            }
        
        self.metrics['ai_calls'][key]['calls'] += 1
        self.metrics['ai_calls'][key]['tokens'] += tokens
        self.metrics['ai_calls'][key]['cost'] += cost
    
    def record_rag_retrieval(self, retrieval_type: str, results_count: int, latency_ms: float):
        """Record RAG retrieval metrics"""
        if retrieval_type not in self.metrics['rag_retrieval']:
            self.metrics['rag_retrieval'][retrieval_type] = {
                'count': 0,
                'total_results': 0,
                'total_latency_ms': 0
            }
        
        metric = self.metrics['rag_retrieval'][retrieval_type]
        metric['count'] += 1
        metric['total_results'] += results_count
        metric['total_latency_ms'] += latency_ms
    
    def record_error(self, error_type: str, error_message: str, context: Dict[str, Any] = None):
        """Record error metrics"""
        if error_type not in self.metrics['errors']:
            self.metrics['errors'][error_type] = {
                'count': 0,
                'messages': [],
                'contexts': []
            }
        
        self.metrics['errors'][error_type]['count'] += 1
        self.metrics['errors'][error_type]['messages'].append(error_message)
        if context:
            self.metrics['errors'][error_type]['contexts'].append(context)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        summary = {
            'requests': {},
            'ai_calls': {},
            'rag_retrieval': {},
            'errors': {},
            'performance': {}
        }
        
        # Request metrics
        for name, data in self.metrics['requests'].items():
            summary['requests'][name] = data['count']
        
        # AI call metrics
        for name, data in self.metrics['ai_calls'].items():
            summary['ai_calls'][name] = {
                'calls': data['calls'],
                'tokens': data['tokens'],
                'cost': data['cost']
            }
        
        # RAG metrics
        for name, data in self.metrics['rag_retrieval'].items():
            avg_results = data['total_results'] / data['count'] if data['count'] > 0 else 0
            avg_latency = data['total_latency_ms'] / data['count'] if data['count'] > 0 else 0
            summary['rag_retrieval'][name] = {
                'count': data['count'],
                'avg_results': avg_results,
                'avg_latency_ms': avg_latency
            }
        
        # Error metrics
        for name, data in self.metrics['errors'].items():
            summary['errors'][name] = data['count']
        
        # Performance metrics
        for name, data in self.metrics['performance'].items():
            avg_duration = data['total_ms'] / data['count'] if data['count'] > 0 else 0
            summary['performance'][name] = {
                'count': data['count'],
                'avg_ms': avg_duration,
                'min_ms': data['min_ms'],
                'max_ms': data['max_ms']
            }
        
        return summary


class RequestContext:
    """
    Request context for distributed tracing
    """
    
    def __init__(self):
        self.request_id = str(uuid.uuid4())
        self.correlation_id = str(uuid.uuid4())
        self.user_id = None
        self.session_id = None
        self.start_time = time.time()
        self.metadata = {}
    
    def set_user_context(self, user_id: str, session_id: str = None):
        """Set user context"""
        self.user_id = user_id
        self.session_id = session_id
    
    def add_metadata(self, key: str, value: Any):
        """Add metadata to context"""
        self.metadata[key] = value
    
    def get_elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds"""
        return (time.time() - self.start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary"""
        return {
            'request_id': self.request_id,
            'correlation_id': self.correlation_id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'elapsed_ms': self.get_elapsed_ms(),
            'metadata': self.metadata
        }


class ObservabilityMiddleware:
    """
    Middleware for automatic observability
    """
    
    def __init__(self):
        self.logger = StructuredLogger('observability')
        self.metrics = MetricsCollector()
        self.context_stack = []
    
    async def __call__(self, request, call_next):
        """FastAPI middleware call method"""
        import time
        start_time = time.time()
        
        # Create request context
        context = RequestContext()
        request_id = request.headers.get("X-Request-ID", context.request_id)
        context.request_id = request_id
        
        self.context_stack.append(context)
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log request
            self.log_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = context.request_id
            
            return response
            
        finally:
            self.context_stack.pop()
    
    @contextmanager
    def request_context(self, request_id: str = None):
        """Create request context"""
        context = RequestContext()
        if request_id:
            context.request_id = request_id
        
        self.context_stack.append(context)
        try:
            yield context
        finally:
            self.context_stack.pop()
    
    def get_current_context(self) -> Optional[RequestContext]:
        """Get current request context"""
        return self.context_stack[-1] if self.context_stack else None
    
    def log_request(self, method: str, path: str, status_code: int, duration_ms: float):
        """Log HTTP request"""
        context = self.get_current_context()
        log_data = {
            'method': method,
            'path': path,
            'status_code': status_code,
            'duration_ms': duration_ms,
            'context': context.to_dict() if context else None
        }
        
        if status_code >= 500:
            self.logger.error(f"HTTP {status_code} {method} {path}", **log_data)
        elif status_code >= 400:
            self.logger.warning(f"HTTP {status_code} {method} {path}", **log_data)
        else:
            self.logger.info(f"HTTP {status_code} {method} {path}", **log_data)
        
        # Record metrics
        self.metrics.increment_counter(f"http_{method.lower()}", {
            'path': path,
            'status': str(status_code)
        })
        self.metrics.record_timing(f"http_request_duration", duration_ms, {
            'method': method,
            'path': path
        })


def track_performance(metric_name: str):
    """Decorator to track function performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                # Record metrics if observability is available
                if hasattr(wrapper, '_observability'):
                    wrapper._observability.metrics.record_timing(
                        metric_name, duration_ms
                    )
                
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                # Record error metrics
                if hasattr(wrapper, '_observability'):
                    wrapper._observability.metrics.record_error(
                        type(e).__name__, str(e), {'duration_ms': duration_ms}
                    )
                
                raise
        return wrapper
    return decorator


# Global observability instance
observability = ObservabilityMiddleware()