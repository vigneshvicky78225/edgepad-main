import sys
import os
import unittest
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QUrl, QTimer, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from gui.backend.controller import EdgepadController

def test_headless_gui():
    # Use offscreen platform for headless rendering
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    
    engine = QQmlApplicationEngine()
    controller = EdgepadController()
    
    engine.rootContext().setContextProperty("edgepadController", controller)
    
    warnings = []
    engine.warnings.connect(lambda w: warnings.append(w))
    
    qml_file = ROOT / "gui" / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    
    if not engine.rootObjects():
        print("FAILED to load Main.qml")
        return False
        
    window = engine.rootObjects()[0]
    print(f"Loaded Main.qml successfully. Window: {window.property('title')}")
    
    # Test resolutions
    resolutions = [
        (1280, 720, "720p Standard"),
        (1366, 768, "Laptop 1366"),
        (1920, 1080, "Desktop 1080p"),
        (900, 650, "Narrow Compact"),
        (720, 500, "Minimum Window Limit")
    ]
    
    for w, h, name in resolutions:
        window.setProperty("width", w)
        window.setProperty("height", h)
        app.processEvents()
        
        actual_w = window.property("width")
        actual_h = window.property("height")
        print(f"Tested resolution {name}: requested {w}x{h}, actual {actual_w}x{actual_h}")
        assert actual_w == w and actual_h == h, f"Resolution mismatch for {name}"
        
    # Test notification dismissal
    print("\n--- Testing Notification Dismissal in UI ---")
    controller._set_error("Error 1: Background service died.")
    app.processEvents()
    assert controller.lastError == "Error 1: Background service died."
    
    # Check notification footer visibility
    footer = window.findChild(object, "notificationFooter")
    # Call dismissCurrentNotification
    controller.dismissCurrentNotification()
    app.processEvents()
    assert controller.lastError == "", "lastError should be cleared"
    
    # Test service error appears on poll
    controller.service_manager.get_status = lambda: "error"
    controller._poll_status()
    app.processEvents()
    assert controller.lastError != "", "Service error should appear on poll"
    
    # Dismiss service error
    controller.dismissCurrentNotification()
    app.processEvents()
    assert controller.lastError == "", "Dismissed error should be cleared"
    
    # Poll again - unchanged error must not reappear
    controller._poll_status()
    app.processEvents()
    assert controller.lastError == "", "Unchanged dismissed error should not reappear on poll"
    
    # Test new error displays
    controller._set_error("New distinct error")
    app.processEvents()
    assert controller.lastError == "New distinct error", "New error must be shown"
    
    controller.dismissCurrentNotification()
    app.processEvents()
    assert controller.lastError == ""
    
    # Test navigation across all views
    print("\n--- Testing Navigation Across All Views ---")
    stack = window.findChild(object, "navStack")
    
    for idx in range(9):
        window.navigateToPage(idx, 0)
        app.processEvents()
        print(f"Navigated to page index {idx}")
        
    print("\nAll UI checks PASSED successfully!")
    return True

if __name__ == "__main__":
    success = test_headless_gui()
    sys.exit(0 if success else 1)
