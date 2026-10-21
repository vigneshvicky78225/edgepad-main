import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QUrl, QTimer, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from gui.backend.controller import EdgepadController

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()
controller = EdgepadController()
engine.rootContext().setContextProperty("edgepadController", controller)

qml_file = ROOT / "gui" / "qml" / "Main.qml"
engine.load(QUrl.fromLocalFile(str(qml_file)))

window = engine.rootObjects()[0]
window.setProperty("width", 1060)
window.setProperty("height", 720)
app.processEvents()

scratch_dir = ROOT / "scratch"
scratch_dir.mkdir(exist_ok=True)

view_names = [
    "dashboard",
    "tap_actions",
    "gestures",
    "calibration",
    "live_tester",
    "devices",
    "diagnostics",
    "about"
]

for idx, name in enumerate(view_names):
    window.navigateToPage(idx, 0)
    app.processEvents()
    out_path = scratch_dir / f"refined_{idx}_{name}.png"
    pix = app.primaryScreen().grabWindow(window.winId())
    pix.save(str(out_path))
    print(f"Captured: {out_path} ({pix.width()}x{pix.height()})")

print("All screenshots successfully captured!")
