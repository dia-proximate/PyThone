"""
Windows Troubleshoot Tool
Single-file Python app using PySide6. Runs on Windows.
Features:
 - Tabbed UI (Network, System)
 - Ping, Tracert, Nslookup with streaming output (no buffer/dồn cục)
 - Get Hostname, Local IP, Serial Number (via wmic)
 - Smooth gradient background and subtle animations

Requirements:
 pip install PySide6

Run:
 python windows_troubleshoot_tool.py

"""
import sys
import shutil
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt, QProcess, QTimer, QPropertyAnimation
import socket
import subprocess

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

# ---- Widgets ----

class GradientWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Windows Troubleshoot Tool')
        self.setMinimumSize(900, 600)
        self.setWindowFlag(Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        # central widget with rounded card
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)

        card = QtWidgets.QFrame()
        card.setObjectName('card')
        card.setStyleSheet('QFrame#card{border-radius:14px; background: rgba(255,255,255,0.06);}')
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)

        header = QtWidgets.QLabel('Windows Troubleshoot Tool')
        header.setStyleSheet('font-size:20px; font-weight:600; color: white;')
        card_layout.addWidget(header)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setStyleSheet('QTabBar::tab{padding:10px 14px; border-radius:8px;}')
        card_layout.addWidget(self.tabs, 1)

        layout.addWidget(card)

        self._make_network_tab()
        self._make_system_tab()

        # subtle shadow
        effect = QtWidgets.QGraphicsDropShadowEffect(blurRadius=30, xOffset=0, yOffset=8)
        effect.setColor(QtGui.QColor(0,0,0,160))
        card.setGraphicsEffect(effect)

        # gradient animation state
        self._grad_offset = 0.0
        self._grad_timer = QTimer(self)
        self._grad_timer.timeout.connect(self._on_grad_tick)
        self._grad_timer.start(40)

        # fade-in animation for card
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
        # animated gradient background
        p = QtGui.QPainter(self)
        r = self.rect()
        grad = QtGui.QLinearGradient(0, 0, r.width(), r.height())
        # change color stops slowly
        t = self._grad_offset
        c1 = QtGui.QColor.fromHsvF((0.55 + t*0.1) % 1.0, 0.6, 0.25)
        c2 = QtGui.QColor.fromHsvF((0.75 - t*0.08) % 1.0, 0.7, 0.18)
        grad.setColorAt(0.0, c1)
        grad.setColorAt(1.0, c2)
        p.fillRect(r, grad)
        super().paintEvent(event)

    # ---- Tabs ----
    def _make_network_tab(self):
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)

        controls = QtWidgets.QHBoxLayout()
        self.net_target = QtWidgets.QLineEdit()
        self.net_target.setPlaceholderText('Enter host or domain, e.g. 8.8.8.8 or example.com')
        self.net_target.setMinimumWidth(300)
        controls.addWidget(self.net_target)

        btn_ping = QtWidgets.QPushButton('Ping')
        btn_ping.clicked.connect(self._do_ping)
        controls.addWidget(btn_ping)

        btn_tracert = QtWidgets.QPushButton('Tracert')
        btn_tracert.clicked.connect(self._do_tracert)
        controls.addWidget(btn_tracert)

        btn_ns = QtWidgets.QPushButton('NSLookup')
        btn_ns.clicked.connect(self._do_nslookup)
        controls.addWidget(btn_ns)

        controls.addStretch()
        layout.addLayout(controls)

        # live output box
        self.net_output = QtWidgets.QPlainTextEdit()
        self.net_output.setReadOnly(True)
        self.net_output.setStyleSheet('background: rgba(0,0,0,0.35); color: #e6f0ff; padding:10px; border-radius:8px;')
        layout.addWidget(self.net_output)

        self.tabs.addTab(w, 'Network')

        # QProcess for streaming
        self.current_process = None

    def _make_system_tab(self):
        w = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(w)

        hostname = socket.gethostname()
        ip = get_local_ip()
        serial = run_wmic_serial()

        self.lbl_hostname = QtWidgets.QLabel(hostname)
        self.lbl_ip = QtWidgets.QLabel(ip)
        self.lbl_serial = QtWidgets.QLabel(serial)

        layout.addRow('Hostname:', self.lbl_hostname)
        layout.addRow('Local IP:', self.lbl_ip)
        layout.addRow('Serial Number:', self.lbl_serial)

        refresh = QtWidgets.QPushButton('Refresh')
        refresh.clicked.connect(self._refresh_system)
        layout.addRow(refresh)

        self.tabs.addTab(w, 'System')

    def _refresh_system(self):
        self.lbl_hostname.setText(socket.gethostname())
        self.lbl_ip.setText(get_local_ip())
        self.lbl_serial.setText(run_wmic_serial())

    # ---- Network commands with streaming ----
    def _start_process(self, args, title=None):
        # stop previous
        if hasattr(self, 'current_process') and self.current_process:
            try:
                self.current_process.kill()
            except Exception:
                pass

        proc = QProcess(self)
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(lambda: self._on_proc_output(proc))
        proc.finished.connect(lambda exitCode, status: self._on_proc_finished(exitCode, status, proc))
        # show header
        header = f"\n=== {title or 'Command'} started ===\n"
        self.net_output.appendPlainText(header)
        # start
        proc.start(args[0], args[1:])
        self.current_process = proc

    def _on_proc_output(self, proc):
        try:
            data = proc.readAllStandardOutput().data().decode(errors='ignore')
            # append incrementally to avoid buffering issues
            self.net_output.moveCursor(QtGui.QTextCursor.End)
            self.net_output.insertPlainText(data)
            self.net_output.moveCursor(QtGui.QTextCursor.End)
        except Exception:
            pass

    def _on_proc_finished(self, exitCode, status, proc):
        footer = f"\n=== finished (code={exitCode}) ===\n"
        self.net_output.appendPlainText(footer)
        if proc is self.current_process:
            self.current_process = None

    def _do_ping(self):
        target = self.net_target.text().strip()
        if not target:
            self.net_output.appendPlainText('Enter a target first.')
            return
        # windows ping default 4, use -n 4
        if shutil.which('ping'):
            self._start_process(['ping', '-n', '4', target], title=f'Ping {target}')
        else:
            self.net_output.appendPlainText('ping not found on system')

    def _do_tracert(self):
        target = self.net_target.text().strip()
        if not target:
            self.net_output.appendPlainText('Enter a target first.')
            return
        if shutil.which('tracert'):
            self._start_process(['tracert', target], title=f'Tracert {target}')
        else:
            self.net_output.appendPlainText('tracert not found on system')

    def _do_nslookup(self):
        target = self.net_target.text().strip()
        if not target:
            self.net_output.appendPlainText('Enter a target first.')
            return
        if shutil.which('nslookup'):
            self._start_process(['nslookup', target], title=f'NSLookup {target}')
        else:
            self.net_output.appendPlainText('nslookup not found on system')

# ---- Main ----

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')

    # global minimal stylesheet for clarity
    app.setStyleSheet('''
        QWidget{font-family:Segoe UI, Arial; font-size:12px}
        QTabWidget::pane { border: none; }
        QTabBar::tab { background: rgba(255,255,255,0.04); color: #e7f0ff; }
        QTabBar::tab:selected { background: rgba(255,255,255,0.08); }
    ''')

    win = GradientWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
