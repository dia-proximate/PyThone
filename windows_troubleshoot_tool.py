import sys, platform, getpass, socket, uuid, subprocess
from PyQt5 import QtWidgets, QtCore

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Windows Troubleshoot Tool")
        self.resize(950, 620)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        # Tabs
        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs)

        # --- Tab Network ---
        self.tab_network = QtWidgets.QWidget()
        self.tabs.addTab(self.tab_network, "Network")
        self._init_tab_network()

        # --- Tab System ---
        self.tab_system = QtWidgets.QWidget()
        self.tabs.addTab(self.tab_system, "System")
        self._init_tab_system()

        # --- Tab Tools ---
        self.tab_tools = QtWidgets.QWidget()
        self.tabs.addTab(self.tab_tools, "Tools")
        self._init_tab_tools()

    # -------------------------------------------------
    def _append_output(self, widget: QtWidgets.QPlainTextEdit, text: str):
        widget.appendPlainText(text.strip())

    # ================= NETWORK TAB =================
    def _init_tab_network(self):
        lay = QtWidgets.QVBoxLayout(self.tab_network)

        input_lay = QtWidgets.QHBoxLayout()
        self.net_target = QtWidgets.QLineEdit()
        self.net_target.setPlaceholderText("Enter host or IP...")
        input_lay.addWidget(self.net_target)

        self.btn_ping = QtWidgets.QPushButton("Ping")
        self.btn_ping.clicked.connect(self._ping_host)
        input_lay.addWidget(self.btn_ping)

        self.btn_tracert = QtWidgets.QPushButton("Tracert")
        self.btn_tracert.clicked.connect(self._tracert_host)
        input_lay.addWidget(self.btn_tracert)

        self.btn_ns = QtWidgets.QPushButton("NSLookup")
        self.btn_ns.clicked.connect(self._nslookup_host)
        input_lay.addWidget(self.btn_ns)

        lay.addLayout(input_lay)

        self.net_output = QtWidgets.QPlainTextEdit()
        self.net_output.setReadOnly(True)
        self.net_output.setStyleSheet("background:black;color:white;font:12px Consolas;")
        lay.addWidget(self.net_output)

    def _ping_host(self):
        target = self.net_target.text().strip()
        if not target:
            self._append_output(self.net_output, "Enter a target first.")
            return
        self._append_output(self.net_output, f"=== Ping {target} started ===")
        cmd = ["ping", target]
        self._run_cmd(cmd, self.net_output)

    def _tracert_host(self):
        target = self.net_target.text().strip()
        if not target:
            self._append_output(self.net_output, "Enter a target first.")
            return
        self._append_output(self.net_output, f"=== Tracert {target} started ===")
        cmd = ["tracert", target]
        self._run_cmd(cmd, self.net_output)

    def _nslookup_host(self):
        target = self.net_target.text().strip()
        if not target:
            self._append_output(self.net_output, "Enter a target first.")
            return
        self._append_output(self.net_output, f"=== NSLookup {target} started ===")
        cmd = ["nslookup", target]
        self._run_cmd(cmd, self.net_output)

    def _run_cmd(self, cmd, output_widget):
        process = QtCore.QProcess(self)
        process.setProgram(cmd[0])
        process.setArguments(cmd[1:])
        process.readyReadStandardOutput.connect(
            lambda: self._append_output(
                output_widget,
                process.readAllStandardOutput().data().decode(errors="ignore"),
            )
        )
        process.readyReadStandardError.connect(
            lambda: self._append_output(
                output_widget,
                process.readAllStandardError().data().decode(errors="ignore"),
            )
        )
        process.finished.connect(
            lambda code, status: self._append_output(output_widget, f"=== finished (code={code}) ===")
        )
        process.start()

    # ================= SYSTEM TAB =================
    def _init_tab_system(self):
        lay = QtWidgets.QVBoxLayout(self.tab_system)

        self.btn_sys_info = QtWidgets.QPushButton("Load System Info")
        self.btn_sys_info.clicked.connect(self._show_system_info)
        lay.addWidget(self.btn_sys_info)

        self.sys_output = QtWidgets.QPlainTextEdit()
        self.sys_output.setReadOnly(True)
        self.sys_output.setStyleSheet("background:black;color:white;font:12px Consolas;")
        lay.addWidget(self.sys_output)

    def _show_system_info(self):
        try:
            hostname = platform.node()
            user = getpass.getuser()
            os_version = f"{platform.system()} {platform.release()} ({platform.version()})"
            processor = platform.processor()
            ip = socket.gethostbyname(socket.gethostname())
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff)
                           for ele in range(0, 8*6, 8)][::-1])
            serial = "Unknown"  # thêm wmic nếu muốn

            formatted = (
                f"Hostname: {hostname}\n"
                f"User: {user}\n"
                f"OS: {os_version}\n"
                f"Processor: {processor}\n"
                f"IP: {ip}\n"
                f"MAC: {mac}\n"
                f"Serial: {serial}\n"
            )
            self._append_output(self.sys_output, formatted)
        except Exception as e:
            self._append_output(self.sys_output, f"Error getting system info: {e}")

    # ================= TOOLS TAB =================
    def _init_tab_tools(self):
        lay = QtWidgets.QVBoxLayout(self.tab_tools)

        # Speedtest
        self.btn_speed = QtWidgets.QPushButton("Run Speedtest")
        self.btn_speed.clicked.connect(self._run_speedtest)
        lay.addWidget(self.btn_speed)

        # TCP Port check
        port_lay = QtWidgets.QHBoxLayout()
        self.host_input = QtWidgets.QLineEdit()
        self.host_input.setPlaceholderText("host")
        port_lay.addWidget(self.host_input)
        self.port_input = QtWidgets.QLineEdit()
        self.port_input.setPlaceholderText("port")
        port_lay.addWidget(self.port_input)

        self.btn_port = QtWidgets.QPushButton("Check Port")
        self.btn_port.clicked.connect(self._check_port)
        port_lay.addWidget(self.btn_port)

        lay.addLayout(port_lay)

        self.tools_output = QtWidgets.QPlainTextEdit()
        self.tools_output.setReadOnly(True)
        self.tools_output.setStyleSheet("background:black;color:white;font:12px Consolas;")
        lay.addWidget(self.tools_output)

    def _run_speedtest(self):
        self._append_output(self.tools_output, "=== Running speedtest-cli ===")
        cmd = ["speedtest"]
        self._run_cmd(cmd, self.tools_output)

    def _check_port(self):
        host = self.host_input.text().strip()
        port_str = self.port_input.text().strip()
        if not (host and port_str.isdigit()):
            self._append_output(self.tools_output, "Enter valid host and numeric port.")
            return
        port = int(port_str)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, port))
            if result == 0:
                self._append_output(self.tools_output, f"{host}:{port} -> OPEN")
            else:
                self._append_output(self.tools_output, f"{host}:{port} -> CLOSED")
            sock.close()
        except Exception as e:
            self._append_output(self.tools_output, f"Error: {e}")

# ================================================================
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
