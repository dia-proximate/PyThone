import subprocess
import socket
import requests
import os
from colorama import Fore, init
import speedtest  # cần cài speedtest-cli
from rich.console import Console
from rich.table import Table

init(autoreset=True)
console = Console()

LOG_FILE = "network_tool.log"


def log_result(text):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n")


def run_command_realtime(cmd, color=Fore.GREEN):
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
            print(color + line.strip())
            log_result(line.strip())
        process.stdout.close()
        process.wait()
    except Exception as e:
        print(Fore.RED + f"Lỗi: {e}")
        log_result(f"Lỗi: {e}")


def ping_host():
    host = input("Nhập IP hoặc domain để ping: ").strip()
    print(Fore.CYAN + f"Đang ping {host}...\n")
    run_command_realtime(["ping", host])


def tracert_host():
    host = input("Nhập IP hoặc domain để tracert: ").strip()
    print(Fore.CYAN + f"Đang tracert {host}...\n")
    run_command_realtime(["tracert", host])


def nslookup_domain():
    domain = input("Nhập domain để nslookup: ").strip()
    print(Fore.CYAN + f"Đang nslookup {domain}...\n")
    run_command_realtime(["nslookup", domain])


def check_tcp_connection():
    host = input("Nhập IP hoặc domain: ").strip()
    port = int(input("Nhập port: ").strip())
    print(Fore.CYAN + f"Đang kiểm tra TCP {host}:{port}...\n")
    try:
        sock = socket.create_connection((host, port), timeout=5)
        print(Fore.GREEN + f"Kết nối tới {host}:{port} thành công")
        log_result(f"Kết nối tới {host}:{port} thành công")
        sock.close()
    except Exception as e:
        print(Fore.RED + f"Không kết nối được {host}:{port} ({e})")
        log_result(f"Không kết nối được {host}:{port} ({e})")


def get_serial_number():
    print(Fore.CYAN + "Đang lấy Serial Number...\n")
    run_command_realtime(
        ["wmic", "bios", "get", "serialnumber"], color=Fore.YELLOW
    )


def open_log_file():
    print(Fore.CYAN + f"Mở log file: {os.path.abspath(LOG_FILE)}\n")
    try:
        os.startfile(LOG_FILE)  # chỉ Windows
    except Exception as e:
        print(Fore.RED + f"Lỗi khi mở log: {e}")


def show_ipconfig():
    print(Fore.CYAN + "Thông tin IP configuration...\n")
    run_command_realtime(["ipconfig", "/all"], color=Fore.MAGENTA)


def check_internet_connectivity():
    print(Fore.CYAN + "Kiểm tra kết nối Internet...\n")
    try:
        r = requests.get("https://www.google.com", timeout=5)
        if r.status_code == 200:
            print(Fore.GREEN + "Internet OK (truy cập được Google)")
            log_result("Internet OK (truy cập được Google)")
        else:
            print(Fore.RED + f"Kết nối lỗi: {r.status_code}")
            log_result(f"Kết nối lỗi: {r.status_code}")
    except Exception as e:
        print(Fore.RED + f"Không có Internet ({e})")
        log_result(f"Không có Internet ({e})")


def clear_log_file():
    try:
        open(LOG_FILE, "w", encoding="utf-8").close()
        print(Fore.GREEN + "Log file đã được xóa sạch.")
    except Exception as e:
        print(Fore.RED + f"Lỗi khi xóa log: {e}")


def run_speedtest():
    print(Fore.CYAN + "Đang chạy speedtest...\n")
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        download = st.download() / 1_000_000  # Mbps
        upload = st.upload() / 1_000_000
        ping = st.results.ping

        # hiển thị bằng rich table
        table = Table(title="Speedtest Result", style="cyan")
        table.add_column("Metric", style="magenta", justify="center")
        table.add_column("Value", style="green", justify="center")

        table.add_row("Ping", f"{ping:.2f} ms")
        table.add_row("Download", f"{download:.2f} Mbps")
        table.add_row("Upload", f"{upload:.2f} Mbps")

        console.print(table)

        result = (f"Ping: {ping:.2f} ms | "
                  f"Download: {download:.2f} Mbps | "
                  f"Upload: {upload:.2f} Mbps")
        log_result("Speedtest -> " + result)
    except Exception as e:
        print(Fore.RED + f"Lỗi speedtest: {e}")
        log_result(f"Lỗi speedtest: {e}")


def main():
    while True:
        print(Fore.CYAN + "\n=== Network Troubleshoot Tool ===")
        print("1. Ping host")
        print("2. Tracert host")
        print("3. Nslookup domain")
        print("4. Check TCP connection")
        print("5. Get Serial Number")
        print("6. Exit")
        print("7. Open log file")
        print("8. Show IP config")
        print("9. Check Internet connectivity")
        print("10. Clear log file")
        print("11. Speedtest")
        print(Fore.YELLOW + f"\n[Log file: {os.path.abspath(LOG_FILE)}]")

        choice = input(Fore.WHITE + "Chọn chức năng (1-11): ").strip()

        if choice == "1":
            ping_host()
        elif choice == "2":
            tracert_host()
        elif choice == "3":
            nslookup_domain()
        elif choice == "4":
            check_tcp_connection()
        elif choice == "5":
            get_serial_number()
        elif choice == "6":
            print(Fore.CYAN + "Thoát chương trình.")
            break
        elif choice == "7":
            open_log_file()
        elif choice == "8":
            show_ipconfig()
        elif choice == "9":
            check_internet_connectivity()
        elif choice == "10":
            clear_log_file()
        elif choice == "11":
            run_speedtest()
        else:
            print(Fore.RED + "Lựa chọn không hợp lệ.")


if __name__ == "__main__":
    main()
