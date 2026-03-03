#!/bin/bash
# Setup script to create cgroup v1 compatible structure for Judge0 isolate sandbox
# This script is run inside the worker container to create the necessary cgroup hierarchy

set -e

echo "[cgroup-setup] Starting cgroup v1 compatibility setup..."

# Check if we need to set up cgroups
if [ -d "/sys/fs/cgroup/memory" ] && [ -f "/sys/fs/cgroup/memory/memory.limit_in_bytes" ]; then
    echo "[cgroup-setup] cgroup v1 memory controller already available"
else
    echo "[cgroup-setup] Setting up cgroup v1 compatibility layer..."
    
    # Mount tmpfs for our cgroup hierarchy if not already mounted
    if ! mountpoint -q /sys/fs/cgroup/memory 2>/dev/null; then
        mkdir -p /sys/fs/cgroup/memory
        mount -t cgroup -o memory cgroup /sys/fs/cgroup/memory 2>/dev/null || {
            # If direct mount fails, try creating the directory structure for isolate
            echo "[cgroup-setup] Direct cgroup mount failed, trying alternative setup..."
            
            # Create box directories that isolate expects
            for i in $(seq 0 100); do
                mkdir -p /sys/fs/cgroup/memory/box-$i 2>/dev/null || true
            done
        }
    fi
    
    # Same for cpuacct
    if ! mountpoint -q /sys/fs/cgroup/cpuacct 2>/dev/null; then
        mkdir -p /sys/fs/cgroup/cpuacct
        mount -t cgroup -o cpuacct cgroup /sys/fs/cgroup/cpuacct 2>/dev/null || true
    fi
fi

# Create box root directory
mkdir -p /var/local/lib/isolate
chmod 755 /var/local/lib/isolate

echo "[cgroup-setup] Setup complete. Starting workers..."

# Execute the original workers script
exec ./scripts/workers
