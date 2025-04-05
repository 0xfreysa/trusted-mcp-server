#!/bin/sh

# Create log directory
mkdir -p /logs

# Start nitriding with logging
nitriding -fqdn example.com -ext-pub-port 443 -intport 8080 -appwebsrv http://127.0.0.1:7047 > /logs/nitriding.log 2>&1 &
NITRIDING_PID=$!
echo "[sh] Started nitriding with PID $NITRIDING_PID."

sleep 1
    
echo "🚀 starting python server"
cd /bin/mcp
pdm run server.py > /logs/server.log 2>&1 &
SERVER_PID=$!
echo "[sh] Python server started with PID $SERVER_PID."

# Function to check if a process is running
is_running() {
  ps -p $1 > /dev/null
  return $?
}

# Monitor processes and restart if needed
while true; do
  if ! is_running $NITRIDING_PID; then
    echo "[sh] Nitriding process died, restarting..."
    nitriding -fqdn example.com -ext-pub-port 443 -intport 8080 -appwebsrv http://127.0.0.1:7047 > /logs/nitriding.log 2>&1 &
    NITRIDING_PID=$!
    echo "[sh] Restarted nitriding with PID $NITRIDING_PID."
  fi
  
  if ! is_running $SERVER_PID; then
    echo "[sh] Python server died, restarting..."
    cd /bin/new
    pdm run server.py > /logs/server.log 2>&1 &
    SERVER_PID=$!
    echo "[sh] Restarted Python server with PID $SERVER_PID."
  fi
  
  sleep 10
done
