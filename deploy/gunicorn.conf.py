# Gunicorn configuration for mcptools.xin

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
# Recommended: (2 x $num_cores) + 1  for I/O bound
# For CPU bound, use $num_cores
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
threads = 2

# Timeout settings
timeout = 120
keepalive = 5
graceful_timeout = 30

# Process naming
proc_name = "mcptools"

# Logging
accesslog = "/var/log/mcptools/access.log"
errorlog = "/var/log/mcptools/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process management
daemon = False
pidfile = "/var/run/mcptools/mcptools.pid"
user = "www-data"
group = "www-data"

# Server mechanics
reload = False
max_requests = 1000
max_requests_jitter = 50
pre_fork_app = True

# SSL (if needed)
# keyfile = "/path/to/key.pem"
# certfile = "/path/to/cert.pem"
