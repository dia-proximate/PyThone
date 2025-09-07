import os
import platform
import socket
import subprocess
import psutil
import requests
import speedtest

def get_host_name():
    print("\n📌 Hostname:", socket.gethostname())

def get_os_version():
    print("\n📌 OS Version:", platform.platform())

def get_ip_address():
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    print("\n📌 Local IP Address:", ip_address)

def ping_google():
    print("\n📡 Pinging Google DNS (8.8.8.8)...")
    os.system("ping 8.8.8.8 -n 4" if platform.system().lower()=="windows" else "ping -c 4 8.8.8.8")

def tracert_google():
    print("\n🛣️ Traceroute to Google DNS (8.8.8.8)...")
    os.system("tracert 8.8.8.8" if platform.system().lower()=="windows" else "traceroute 8.8.8.8")

def get_public_ip():
    try:
        public_ip = requests.get("https://api.ipify.org").text
        print("\n🌍 Public IP Address:", public_ip)
    except:
        print("\n⚠️ Could not fetch Public IP")

def get_network_interfaces():
    print("\n📡 Network Interfaces & Status:")
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    for iface, addr_list in addrs.items():
        print(f"\n🔹 Interface: {iface}")
        for addr in addr_list:
            print(f"   - {addr.family.name}: {addr.address}")
        if iface in stats:
            print(f"   - Status: {'Up' if stats[iface].isup else 'Down'}")

def quick_diagnostic():
    print("\n🚀 Running Quick Diagnostic (Ping Google + Public IP)...")
    ping_google()
    get_public_ip()

def run_speedtest():
    print("\n⚡ Running Speedtest...")
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        download = st.download() / 1_000_000  # Mbps
        upload = st.upload() / 1_000_000      # Mbps
        print(f"   📥 Download Speed: {download:.2f} Mbps")
        print(f"   📤 Upload Speed: {upload:.2f} Mbps")
    except Exception as e:
        print("⚠️ Speedtest failed:", e)

def menu():
    while True:
        print("\n========== 🌐 Network Diagnostic Tool V2 ==========")
        print("1️⃣  Get Hostname")
        print("2️⃣  Get OS Version")
        print("3️⃣  Get Local IP Address")
        print("4️⃣  Get Public IP Address")
        print("5️⃣  Ping Google (8.8.8.8)")
        print("6️⃣  Traceroute to Google")
        print("7️⃣  Show Network Interfaces")
        print("8️⃣  Run SpeedTest")
        print("9️⃣  Quick Diagnostic (Ping + Public IP)")
        print("0️⃣  Exit")
        
        choice = input("\n👉 Enter your choice: ")

        if choice == "1":
            get_host_name()
        elif choice == "2":
            get_os_version()
        elif choice == "3":
            get_ip_address()
        elif choice == "4":
            get_public_ip()
        elif choice == "5":
            ping_google()
        elif choice == "6":
            tracert_google()
        elif choice == "7":
            get_network_interfaces()
        elif choice == "8":
            run_speedtest()
        elif choice == "9":
            quick_diagnostic()
        elif choice == "0":
            print("\n✅ Exiting tool. Goodbye!\n")
            break
        else:
            print("\n⚠️ Invalid choice, try again!")

if __name__ == "__main__":
    menu()
