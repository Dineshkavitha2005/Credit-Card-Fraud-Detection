"""
Gunicorn Production Server Configuration
Optimized for Credit Card Fraud Detection Flask & ML Application
"""
import os
import multiprocessing

# Network Binding
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
backlog = 2048

# Worker Processes & Concurrency
# Default to 4 workers or formula ((2 * cores) + 1), configurable via environment
default_workers = int(os.getenv('WORKERS', '4'))
workers = max(1, default_workers)
worker_class = os.getenv('WORKER_CLASS', 'gthread')
threads = int(os.getenv('THREADS', '2'))
worker_connections = 1000

# Lifecycle & Timeouts
timeout = int(os.getenv('TIMEOUT', '120'))
graceful_timeout = int(os.getenv('GRACEFUL_TIMEOUT', '30'))
keepalive = int(os.getenv('KEEPALIVE', '5'))

# Memory & Worker Recycling (prevents memory creep from ML/pandas cache)
max_requests = int(os.getenv('MAX_REQUESTS', '1000'))
max_requests_jitter = int(os.getenv('MAX_REQUESTS_JITTER', '50'))

# Logging to stdout/stderr (standard container practice)
accesslog = '-'
errorlog = '-'
loglevel = os.getenv('LOG_LEVEL', 'info').lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" (%(D)s µs)'
capture_output = True

# Process Naming & Security
proc_name = 'fraud_detection_gunicorn'
preload_app = False  # Allows clean DB connection lifecycle across worker forks

def on_starting(server):
    server.log.info("Starting Credit Card Fraud Detection WSGI Server (Gunicorn)...")

def when_ready(server):
    server.log.info(f"Server is ready. Listening at: {bind} [Workers: {workers}, Threads: {threads}]")

def worker_int(worker):
    worker.log.info("Worker received INT or QUIT signal")

def worker_abort(worker):
    worker.log.error("Worker received SIGABRT signal")
