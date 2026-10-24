"""
Entrypoint launcher for Personal Expense Tracker.
Runs the Flask server and displays access links for Desktop, Tablet, and Mobile.
"""
import socket
import webbrowser
import os
import sys

def get_local_ip():
    """Detect local LAN IP address to allow phones and tablets on same Wi-Fi to connect."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def find_available_port(start_port=5000, max_attempts=20):
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start_port

if __name__ == "__main__":
    from app import app
    
    port = find_available_port(5000)
    local_ip = get_local_ip()
    
    desktop_url = f"http://localhost:{port}"
    network_url = f"http://{local_ip}:{port}"
    
    print("\n" + "=" * 64)
    print("  FinanceFlow - Personal Expense Tracker Web App")
    print("=" * 64)
    print(f"  * Desktop Web App:   {desktop_url}")
    print(f"  * Tablet / Mobile:   {network_url}  (same Wi-Fi)")
    print("  * Database:          SQLite (expenses.db)")
    print("  * Excel Export:      Enabled (.xlsx multi-sheet)")
    print("=" * 64)
    print("  Press Ctrl+C to stop the server.\n")
    
    # Open default browser on desktop launch
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        try:
            webbrowser.open(desktop_url)
        except Exception:
            pass

    app.run(host="0.0.0.0", port=port, debug=False)
