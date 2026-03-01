import time
import os
import psutil

# --- Configuration ---
CPU_IDLE_THRESHOLD = 5.0   # If CPU is under 5%, we consider the server "idle"
MAX_IDLE_MINUTES = 30      # Shut down after 30 consecutive minutes of being idle
CHECK_INTERVAL = 60        # Check the CPU every 60 seconds

idle_counter = 0

print(f"Starting Autoshutdown Monitor. Threshold: CPU < {CPU_IDLE_THRESHOLD}% for {MAX_IDLE_MINUTES} mins.")

while True:
    try:
        # Measure CPU usage over a 5-second sample window for accuracy
        cpu_usage = psutil.cpu_percent(interval=5)
        
        # Check if anyone is actively typing in the SSH terminal
        ssh_sessions = int(os.popen('who | wc -l').read().strip())
        
        if cpu_usage < CPU_IDLE_THRESHOLD and ssh_sessions == 0:
            idle_counter += 1
            print(f"Server is idle (CPU: {cpu_usage}%). Idle for {idle_counter}/{MAX_IDLE_MINUTES} minutes.")
            
            if idle_counter >= MAX_IDLE_MINUTES:
                print("🚨 Max idle time reached. Shutting down the EC2 instance NOW.")
                os.system("sudo shutdown -h now")
                break
        else:
            if idle_counter > 0:
                print(f"Activity detected! (CPU: {cpu_usage}%, SSH: {ssh_sessions}). Resetting timer.")
            idle_counter = 0  # Reset the clock if you run a scan or log in
            
        time.sleep(CHECK_INTERVAL - 5) # Sleep for the rest of the minute
        
    except Exception as e:
        print(f"Error in monitor: {e}")
        time.sleep(CHECK_INTERVAL)