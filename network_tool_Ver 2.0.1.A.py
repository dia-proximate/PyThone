"""
Windows Troubleshoot Tool
Fixed: improved contrast, fixed duplicate "Enter a target first." messages, disabled/enabled buttons during commands, safer thread->UI updates.
Requirements:
 pip install PySide6 requests speedtest-cli
Run:
 python windows_troubleshoot_tool.py
"""
import sys, shutil, socket, subprocess, requests, threading, os, tempfile
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt, QProcess, QTimer, QPropertyAnimation
import speedtest

# ---- Helpers ----

def run_wmic_serial():
    try:
        out = subprocess.check_output(['wmic', 'bios', 'get', 'serialnumber'], stderr=subprocess.DEVNULL, text=True)
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        return lines[1] if len(lines) > 1 else 'Unknown'
    except Exception:
        return 'Unavailable'


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return 'Unknown'

# ---- UI ----
class GradientWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Windows Troubleshoot Tool')
        self.setMinimumSize(900, 600)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)

        card = QtWidgets.QFrame()
        card.setObjectName('card')
        card.setStyleSheet('QFrame#card{border-radius:14px; background: rgba(255,255,255,0.04);}')
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)

        header = QtWidgets.QLabel('Windows Troubleshoot Tool')
        header.setStyleSheet('font-size:20px; font-weight:600; color: #ffffff;')
        card_layout.addWidget(header)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setStyleSheet('QTabBar::tab{padding:10px 14px; border-radius:8px; color:#ffffff;}')
        card_layout.addWidget(self.tabs, 1)
        layout.addWidget(card)

        self._make_network_tab()
        self._make_system_tab()
        self._make_tools_tab()

        effect = QtWidgets.QGraphicsDropShadowEffect(blurRadius=30, xOffset=0, yOffset=8)
        effect.setColor(QtGui.QColor(0,0,0,160))
        card.setGraphicsEffect(effect)

        self._grad_offset = 0.0
        self._grad_timer = QTimer(self)
        self._grad_timer.timeout.connect(self._on_grad_tick)
        self._grad_timer.start(45)

        self._fade_anim = QPropertyAnimation(card, b'windowOpacity')
        self._fade_anim.setDuration(600)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

    def _on_grad_tick(self):
        self._grad_offset += 0.002
        if self._grad_offset >= 1.0:
            self._grad_offset = 0.0
        self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        r = self.rect()
        grad = QtGui.QLinearGradient(0, 0, r.width(), r.height())
        t = self._grad_offset
        # brighter gradient for readability
        c1 = QtGui.QColor.fromHsvF((0.55 + t*0.1) % 1.0, 0.45, 0.72)
        c2 = QtGui.QColor.fromHsvF((0.75 - t*0.08) % 1.0, 0.38, 0.62)
        grad.setColorAt(0.0, c1)
        grad.setColorAt(1.0, c2)
        p.fillRect(r, grad)
        super().paintEvent(event)

    # ---- utility for output to avoid duplicate lines ----
    def _last_non_empty_line(self):
        lines = [l for l in self.net_output.toPlainText().splitlines() if l.strip()]
        return lines[-1] if lines else ''

    def _append_output(self, text):
        text = str(text)
        last = self._last_non_empty_line()
        # avoid repeating the same message consecutively
        if last.strip() == text.strip():
            return
        self.net_output.appendPlainText(text)

    # ---- Tabs ----
    def _make_network_tab(self):
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)

        controls = QtWidgets.QHBoxLayout()
        self.net_target = QtWidgets.QLineEdit()
        self.net_target.setPlaceholderText('Enter host or domain, e.g. 8.8.8.8 or example.com')
        self.net_target.setMinimumWidth(300)
        controls.addWidget(self.net_target)

        self.btn_ping = QtWidgets.QPushButton('Ping')
        self.btn_ping.clicked.connect(self._do_ping)
        controls.addWidget(self.btn_ping)

        self.btn_tracert = QtWidgets.QPushButton('Tracert')
        self.btn_tracert.clicked.connect(self._do_tracert)
        controls.addWidget(self.btn_tracert)

        self.btn_ns = QtWidgets.QPushButton('NSLookup')
        self.btn_ns.clicked.connect(self._do_nslookup)
        controls.addWidget(self.btn_ns)

        controls.addStretch()
        layout.addLayout(controls)

        self.net_output = QtWidgets.QPlainTextEdit()
        self.net_output.setReadOnly(True)
        self.net_output.setStyleSheet(
            'background: rgba(10,10,20,0.86); color: #ffffff; padding:10px; border-radius:8px; font-family:Consolas, "Courier New", monospace; font-size:12px;'
        )
        layout.addWidget(self.net_output)

        self.tabs.addTab(w, 'Network')
        self.current_process = None

    def _make_system_tab(self):
        w = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(w)
        hostname = socket.gethostname()
        ip = get_local_ip()
        serial = run_wmic_serial()

        self.lbl_hostname = QtWidgets.QLabel(hostname)
        self.lbl_hostname.setStyleSheet('color:#ffffff;')
        self.lbl_ip = QtWidgets.QLabel(ip)
        self.lbl_ip.setStyleSheet('color:#ffffff;')
        self.lbl_serial = QtWidgets.QLabel(serial)
        self.lbl_serial.setStyleSheet('color:#ffffff;')

        layout.addRow('Hostname:', self.lbl_hostname)
        layout.addRow('Local IP:', self.lbl_ip)
        layout.addRow('Serial Number:', self.lbl_serial)

        refresh = QtWidgets.QPushButton('Refresh')
        refresh.clicked.connect(self._refresh_system)
        layout.addRow(refresh)

        self.tabs.addTab(w, 'System')

    def _make_tools_tab(self):
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        tips = QtWidgets.QLabel('Extra IT Support tools: TCP Port Check, Speedtest, Log Upload, Send Email')
        tips.setStyleSheet('color:#ffffff; font-size:14px;')
        layout.addWidget(tips)

        # TCP port check
        port_layout = QtWidgets.QHBoxLayout()
        self.port_host = QtWidgets.QLineEdit()
        self.port_host.setPlaceholderText('Host')
        self.port_port = QtWidgets.QLineEdit()
        self.port_port.setPlaceholderText('Port')
        port_btn = QtWidgets.QPushButton('Check TCP Port')
        port_btn.clicked.connect(self._check_tcp_port)
        port_layout.addWidget(self.port_host)
        port_layout.addWidget(self.port_port)
        port_layout.addWidget(port_btn)
        layout.addLayout(port_layout)

        self.port_result = QtWidgets.QLabel('')
        self.port_result.setStyleSheet('color:#ffffff;')
        layout.addWidget(self.port_result)

        # Speedtest
        btn_speed = QtWidgets.QPushButton('Run Speedtest')
        btn_speed.clicked.connect(self._run_speedtest)
        layout.addWidget(btn_speed)
        self.speed_output = QtWidgets.QPlainTextEdit()
        self.speed_output.setReadOnly(True)
        self.speed_output.setStyleSheet('background: rgba(10,10,20,0.86); color:#ffffff;')
        layout.addWidget(self.speed_output)

        btn_upload = QtWidgets.QPushButton('Upload Logs to Server')
        btn_upload.clicked.connect(self._upload_logs)
        layout.addWidget(btn_upload)

        btn_email = QtWidgets.QPushButton('Send Report via Email')
        btn_email.clicked.connect(self._send_email)
        layout.addWidget(btn_email)
        layout.addStretch()
        self.tabs.addTab(w, 'Tools')

    # ---- Refresh ----
    def _refresh_system(self):
        self.lbl_hostname.setText(socket.gethostname())
        self.lbl_ip.setText(get_local_ip())
        self.lbl_serial.setText(run_wmic_serial())

    # ---- Process streaming ----
    def _set_network_buttons_enabled(self, enabled: bool):
        self.btn_ping.setEnabled(enabled)
        self.btn_tracert.setEnabled(enabled)
        self.btn_ns.setEnabled(enabled)

    def _start_process(self, args, title=None):
        if self.current_process:
            try:
                self.current_process.kill()
            except Exception:
                pass
        proc = QProcess(self)
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(lambda: self._on_proc_output(proc))
        proc.finished.connect(lambda exitCode, status: self._on_proc_finished(exitCode, status, proc))
        self._append_output(f"\n=== {title or 'Command'} started ===\n")
        started = proc.start(args[0], args[1:])
        # disable buttons while running
        self._set_network_buttons_enabled(False)
        self.current_process = proc
        if not started:
            self._append_output('Failed to start process')
            self._set_network_buttons_enabled(True)

    def _on_proc_output(self, proc):
        try:
            data = proc.readAllStandardOutput().data().decode(errors='ignore')
            # append raw stream
            self.net_output.moveCursor(QtGui.QTextCursor.End)
            self.net_output.insertPlainText(data)
            self.net_output.moveCursor(QtGui.QTextCursor.End)
        except Exception:
            pass

    def _on_proc_finished(self, exitCode, status, proc):
        self._append_output(f"\n=== finished (code={exitCode}) ===\n")
        if proc is self.current_process:
            self.current_process = None
        # re-enable buttons
        self._set_network_buttons_enabled(True)

    # ---- Network actions ----
    def _do_ping(self):
        target = self.net_target.text().strip()
        if not target:
            self._append_output('Enter a target first.')
            return
        if shutil.which('ping'):
            self._start_process(['ping', '-n', '4', target], title=f'Ping {target}')
        else:
            self._append_output('ping not found')

    def _do_tracert(self):
        target = self.net_target.text().strip()
        if not target:
            self._append_output('Enter a target first.')
            return
        if shutil.which('tracert'):
            self._start_process(['tracert', target], title=f'Tracert {target}')
        else:
            self._append_output('tracert not found')

    def _do_nslookup(self):
        target = self.net_target.text().strip()
        if not target:
            self._append_output('Enter a target first.')
            return
        if shutil.which('nslookup'):
            self._start_process(['nslookup', target], title=f'NSLookup {target}')
        else:
            self._append_output('nslookup not found')

    # ---- TCP Port ----
    def _check_tcp_port(self):
        host = self.port_host.text().strip()
        port_text = self.port_port.text().strip()
        if not host or not port_text.isdigit():
            self.port_result.setText('Invalid host or port')
            return
        port = int(port_text)
        def worker():
            s = socket.socket()
            s.settimeout(3)
            try:
                s.connect((host, port))
                msg = f'{host}:{port} reachable'
            except Exception:
                msg = f'{host}:{port} unreachable'
            finally:
                try: s.close()
                except Exception: pass
            QtCore.QTimer.singleShot(0, lambda: self.port_result.setText(msg))
        threading.Thread(target=worker, daemon=True).start()

    # ---- Speedtest ----
    def _run_speedtest(self):
        self.speed_output.setPlainText('Running speedtest...')
        def worker():
            try:
                st = speedtest.Speedtest()
                st.get_best_server()
                down = st.download() / 1e6
                up = st.upload() / 1e6
                res = f'Download: {down:.2f} Mbps\nUpload: {up:.2f} Mbps'
            except Exception as e:
                res = f'Speedtest failed: {e}'
            QtCore.QTimer.singleShot(0, lambda: self.speed_output.setPlainText(res))
        threading.Thread(target=worker, daemon=True).start()

    # ---- Upload logs (runs in background) ----
    def _upload_logs(self):
        def worker():
            try:
                logs = self.net_output.toPlainText().encode('utf-8')
                r = requests.post('https://example.com/upload', files={'log': ('troubleshoot.txt', logs)})
                QtCore.QTimer.singleShot(0, lambda: QtWidgets.QMessageBox.information(self, 'Upload', f'Status {r.status_code}'))
            except Exception as e:
                QtCore.QTimer.singleShot(0, lambda: QtWidgets.QMessageBox.warning(self, 'Upload failed', str(e)))
        threading.Thread(target=worker, daemon=True).start()

    # ---- Email (placeholder) ----
    def _send_email(self):
        # save current output to temporary file and show path
        try:
            tmp = os.path.join(tempfile.gettempdir(), 'troubleshoot_report.txt')
            with open(tmp, 'w', encoding='utf-8') as f:
                f.write(self.net_output.toPlainText())
            QtWidgets.QMessageBox.information(self, 'Email', f'Log saved to {tmp}. Integrate SMTP to send automatically.')
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, 'Email Error', str(e))

# ---- Main ----

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')
    # global stylesheet to ensure buttons readable
    app.setStyleSheet('''
        QWidget{font-family:Segoe UI; font-size:12px; color:#ffffff;}
        QTabWidget::pane { border: none; }
        QTabBar::tab:selected { background: rgba(255,255,255,0.10); }
        QPushButton{ background: rgba(255,255,255,0.06); color:#ffffff; border-radius:6px; padding:6px 10px; }
        QPushButton:disabled{ background: rgba(255,255,255,0.02); color: rgba(255,255,255,0.6); }
    ''')
    win = GradientWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
