import subprocess
import socket
import getpass
import platform
import datetime
import os
import shutil
from rich.console import Console
from rich.prompt import Prompt

console = Console()

# ========== Config ==========
LOG_DIR = r"C:\NetworkToolLogs"   # thư mục log local
LOG_FILE = os.path.join(LOG_DIR, "network_tool.log")

# Shared folder (cần thay đổi theo môi trường thật)
SHARED_FOLDER = r"\\server\share\NetworkLogs"

# Đảm bảo thư mục log local tồn tại
os.makedirs(LOG_DIR, exist_ok=True)


# ========== Logging ==========
def write_log(text):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now()}] {text}\n")


# ========== Functions ==========
def ping_host():
    host = Prompt.ask("Enter host (IP/domain)")
    try:
        process = subprocess.Popen(["ping", host], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            console.print(line.strip(), style="cyan")
            write_log(line.strip())
    except Exception as e:
        console.print(f"Error: {e}", style="bold red")
        write_log(f"Ping error: {e}")


def tracert_host():
    host = Prompt.ask("Enter host (IP/domain)")
    try:
        process = subprocess.Popen(["tracert", host], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            console.print(line.strip(), style="yellow")
            write_log(line.strip())
    except Exception as e:
        console.print(f"Error: {e}", style="bold red")
        write_log(f"Tracert error: {e}")


def nslookup_domain():
    domain = Prompt.ask("Enter domain")
    try:
        process = subprocess.Popen(["nslookup", domain], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            console.print(line.strip(), style="green")
            write_log(line.strip())
    except Exception as e:
        console.print(f"Error: {e}", style="bold red")
        write_log(f"Nslookup error: {e}")


def check_tcp_port():
    host = Prompt.ask("Enter host (IP/domain)")
    port = int(Prompt.ask("Enter port"))
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        if result == 0:
            msg = f"Port {port} on {host} is OPEN"
            console.print(msg, style="bold green")
        else:
            msg = f"Port {port} on {host} is CLOSED"
            console.print(msg, style="bold red")
        write_log(msg)
        sock.close()
    except Exception as e:
        console.print(f"Error: {e}", style="bold red")
        write_log(f"TCP check error: {e}")


def get_serial_number():
    try:
        cmd = ["powershell", "-Command", "(Get-WmiObject win32_bios).SerialNumber"]
        serial = subprocess.check_output(cmd, text=True).strip()
        if serial:
            console.print(f"Serial Number: {serial}", style="bold magenta")
            write_log(f"Serial Number: {serial}")
        else:
            console.print("Serial Number: N/A", style="bold red")
            write_log("Serial Number: N/A")
    except Exception as e:
        console.print(f"Error: {e}", style="bold red")
        write_log(f"Serial error: {e}")


def get_hostname():
    hostname = socket.gethostname()
    console.print(f"Hostname: {hostname}", style="bold blue")
    write_log(f"Hostname: {hostname}")


def get_username():
    username = getpass.getuser()
    console.print(f"Username: {username}", style="bold blue")
    write_log(f"Username: {username}")


def get_os_version():
    os_version = platform.platform()
    console.print(f"OS Version: {os_version}", style="bold blue")
    write_log(f"OS Version: {os_version}")


def get_ip_address():
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        console.print(f"IP Address: {ip}", style="bold blue")
        write_log(f"IP Address: {ip}")
    except Exception as e:
        console.print(f"Error: {e}", style="bold red")
        write_log(f"IP error: {e}")


def quick_diagnostic():
    console.print("[Quick Diagnostic Running...]", style="bold yellow")
    get_hostname()
    get_username()
    get_os_version()
    get_ip_address()
    get_serial_number()
    console.print("[Quick Diagnostic Completed - Results logged]", style="bold green")


def show_log_path():
    console.print(f"Log file is saved at: {LOG_FILE}", style="bold cyan")


def send_log_to_shared():
    try:
        os.makedirs(SHARED_FOLDER, exist_ok=True)
        dest = os.path.join(SHARED_FOLDER, os.path.basename(LOG_FILE))
        shutil.copy(LOG_FILE, dest)
        console.print(f"Log file copied to shared folder: {dest}", style="bold green")
        write_log(f"Log copied to shared folder: {dest}")
    except Exception as e:
        console.print(f"Error copying log: {e}", style="bold red")
        write_log(f"Shared log copy error: {e}")


# ========== Menu ==========
def menu():
    while True:
        console.print("\n=== Network Troubleshooting Tool V2.1 ===", style="bold underline")
        console.print("1. Ping Host", style="cyan")
        console.print("2. Traceroute to Host", style="cyan")
        console.print("3. Nslookup Domain", style="cyan")
        console.print("4. Check TCP Port Connection", style="cyan")
        console.print("5. Get Serial Number", style="magenta")
        console.print("6. Get Hostname", style="blue")
        console.print("7. Get Username", style="blue")
        console.print("8. Get OS Version", style="blue")
        console.print("9. Get IP Address", style="blue")
        console.print("10. Quick Diagnostic (Hostname, Username, OS, IP, Serial)", style="yellow")
        console.print("11. Show Log File Path", style="cyan")
        console.print("12. Send Log to Shared Folder", style="green")
        console.print("0. Exit", style="red")

        choice = Prompt.ask("Select option", choices=[str(i) for i in range(13)])

        if choice == "1":
            ping_host()
        elif choice == "2":
            tracert_host()
        elif choice == "3":
            nslookup_domain()
        elif choice == "4":
            check_tcp_port()
        elif choice == "5":
            get_serial_number()
        elif choice == "6":
            get_hostname()
        elif choice == "7":
            get_username()
        elif choice == "8":
            get_os_version()
        elif choice == "9":
            get_ip_address()
        elif choice == "10":
            quick_diagnostic()
        elif choice == "11":
            show_log_path()
        elif choice == "12":
            send_log_to_shared()
        elif choice == "0":
            console.print("Exiting tool...", style="bold red")
            break


if __name__ == "__main__":
    menu()
