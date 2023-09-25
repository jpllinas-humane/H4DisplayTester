"""
A python script for enhanced laser display projection and error detection.

Taifu (Tommy) Li

July 2023
"""

# Imports ---------------------------------------------------------------------
import sys, os
import subprocess
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap

# Interactive GUI -------------------------------------------------------------
class ImageLabel(QLabel):
    def __init__(self):
        super().__init__()

        self.setAlignment(Qt.AlignCenter)
        self.setText('\n\n Drop Display Here \n\n')
        self.setStyleSheet('''
            QLabel{
                border: 2px dashed #aaa
            }
        ''')

    def setPixmap(self, image):
        super().setPixmap(image)

class AppDemo(QWidget):
    def __init__(self):
        super().__init__()
        self.serial_nums = self.get_serial_num()
        self.resize(400, 400)
        self.setAcceptDrops(True)

        mainLayout = QVBoxLayout()

        self.photoViewer = ImageLabel()
        mainLayout.addWidget(self.photoViewer)

        self.printButton = QPushButton("Project Image", self)
        self.printButton.clicked.connect(self.project_image)
        mainLayout.addWidget(self.printButton)

        self.printButton = QPushButton("Shut Down H4 >>> Ship mode", self)
        self.printButton.clicked.connect(self.shutdown)
        mainLayout.addWidget(self.printButton)

        self.setLayout(mainLayout)

    def get_serial_num(self):
        """
        Returns a list of serial numbers of connected adb devices.
        """
        serial_nums = []
        result = subprocess.run(["adb", "devices"], stdout=subprocess.PIPE)
        lines = result.stdout.decode('utf-8').strip().split('\n')
        for line in lines[1:]:
            serial_num = line.split("\t")[0]
            serial_nums.append(serial_num)

        print("Connected devices: ", serial_nums)
        return serial_nums

    def dragEnterEvent(self, event):
        if event.mimeData().hasImage:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasImage:
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasImage:
            event.setDropAction(Qt.CopyAction)
            file_path = event.mimeData().urls()[0].toLocalFile()
            self.set_image(file_path)
            event.accept()
        else:
            event.ignore()

    def set_image(self, file_path):
        self.photoViewer.setPixmap(QPixmap(file_path))
        self.file_path = file_path
        self.image_name = os.path.basename(file_path)

    def project_image(self):
        if hasattr(self, 'file_path'):
            self.wipe_image()
            print(f"Image path local: {self.file_path}")
            print(f"Image name: {self.image_name}")
            for serial_num in self.serial_nums:
                self.upload_image(serial_num, self.file_path)
                self.display_image(serial_num, self.image_name)
        else:
            print("No image loaded.")

    def send_keycode(self, serial_num, keycode: str) -> None:
        subprocess.call(["adb", "-s", serial_num, "shell", "input", "keyevent", f"KEYCODE_{keycode.upper()}"])

    def unlock_device(self, serial_num) -> None:
        self.send_keycode(serial_num, "wakeup")
        self.send_keycode(serial_num, "menu")

    def preflight(self, serial_num) -> None:
        subprocess.call(["adb", "-s", serial_num, "wait-for-device", "root"])
        self.unlock_device(serial_num)
        subprocess.call(["adb", "-s", serial_num, "shell", "cmd", "SurfaceFlinger", "display-features", "disable-mesh-rendering"])
        subprocess.call(["adb", "-s", serial_num, "shell", "cmd", "power", "disable-humane-display-controller"])
        subprocess.call(["adb", "-s", serial_num, "shell", "cmd", "package", "disable", "humane.experience.onboarding/.OnboardingHome"])
        subprocess.call(["adb", "-s", serial_num, "shell", "ats", "display", "-screen", "on"])
        subprocess.call(["adb", "-s", serial_num, "shell", "setenforce", "0"])
        subprocess.call(["adb", "-s", serial_num, "shell", "settings", "put", "global", "hidden_api_policy", "1"])
        subprocess.call(["adb", "-s", serial_num, "shell", "settings", "put", "global", "hidden_api_blacklist_exemptions", "\*"])
        subprocess.call(["adb", "-s", serial_num, "shell", "settings", "put", "global", "policy_control", "immersive.full=*"])
        subprocess.call(["adb", "-s", serial_num, "shell", "locksettings", "set-disabled", "true"])
        subprocess.call(["adb", "-s", serial_num, "shell", "settings", "put", "system", "screen_off_timeout", "2147483647"])

    def upload_image(self, serial_num, local_path_to_image) -> None:
        # Check if directory exists on the device
        result = subprocess.run(["adb", "-s", serial_num, "shell", "ls", "/data/tommy_temp_display_storage"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(result.stderr.decode('utf-8'))
        # If directory doesn't exist, create it
        if 'No such file or directory' in result.stderr.decode('utf-8'):
            subprocess.call(["adb", "-s", serial_num, "shell", "mkdir", "/data/tommy_temp_display_storage"])
            print("New dir created")
            
        subprocess.call(["adb", "-s", serial_num, "push", f"{local_path_to_image}", "/data/tommy_temp_display_storage"])

    def display_image(self, serial_num, image_name) -> None:
        subprocess.call(["adb", "-s", serial_num, "shell", "ats", "display", "-screen", "on"])
        subprocess.call(["adb", "-s", serial_num, "shell", "cmd", "SurfaceFlinger", "bypass-video", "predistort", f"/data/tommy_temp_display_storage/{image_name}"])
        print("Image displayed from" + serial_num)
        
    def wipe_image(self) -> None:
        for serial_num in self.serial_nums:
            # Check if directory exists on the device
            result = subprocess.run(["adb", "-s", serial_num, "shell", "ls", "/data/tommy_temp_display_storage"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(result.stderr.decode('utf-8'))
            # If directory doesn't exist, create it
            if 'No such file or directory' in result.stderr.decode('utf-8'):
                subprocess.call(["adb", "-s", serial_num, "shell", "mkdir", "/data/tommy_temp_display_storage"])
                print("New dir created")

            subprocess.call(["adb", "-s", serial_num, "shell", "rm", "-rf", "/data/tommy_temp_display_storage/*"])

    def shutdown(self) -> None:
        for serial_num in self.serial_nums:
            subprocess.call(["adb", "-s", serial_num, "shell", "reboot", "shipmode"])

if __name__ == '__main__':
    app = QApplication(sys.argv)
    demo = AppDemo()
    for serial_num in demo.serial_nums:
        demo.preflight(serial_num)
    demo.show()
    sys.exit(app.exec_())
