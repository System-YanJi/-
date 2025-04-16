#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
可视化翻译工具
支持文本输入翻译和截图保存功能
百度OCR依赖，适合打包为exe
"""

import sys
import os
import warnings

# 忽略警告
warnings.filterwarnings("ignore")
os.environ['PYTHONWARNINGS'] = 'ignore'

# 现在导入其他模块
import time
import hashlib
import random
import requests
import base64
from datetime import datetime
import keyboard
import warnings

# 忝略其他警告
warnings.filterwarnings("ignore")
os.environ['PYTHONWARNINGS'] = 'ignore'
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QPushButton, QTextEdit, QComboBox,
                            QLabel, QMessageBox, QSplitter, QShortcut, QStatusBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPoint, QUrl, QTimer
from PyQt5.QtGui import QPixmap, QKeySequence, QFont, QDesktopServices, QClipboard, QImage, QIcon
import numpy as np
from PIL import Image, ImageGrab

# 导入配置
import config

class ScreenshotThread(QThread):
    """截图线程，避免截图时界面卡顿"""
    screenshot_taken = pyqtSignal(object)

    def run(self):
        try:
            # 延迟一小段时间，让用户有时间切换到目标窗口
            time.sleep(0.5)
            # 截取全屏
            screenshot = ImageGrab.grab()
            # 转换为numpy数组，方便后续处理
            screenshot_np = np.array(screenshot)
            self.screenshot_taken.emit(screenshot_np)
        except Exception as e:
            self.screenshot_taken.emit(None)


# OCR识别线程
class OCRThread(QThread):
    """进行OCR识别的线程"""
    ocr_completed = pyqtSignal(str)

    def __init__(self, image, parent=None):
        super().__init__(parent)
        self.image = image
        self.parent = parent

    def run(self):
        try:
            # 调用OCR识别
            if hasattr(self.parent, 'ocr_with_baidu_api'):
                text = self.parent.ocr_with_baidu_api(self.image)
                self.ocr_completed.emit(text)
            else:
                self.ocr_completed.emit("无法调用OCR识别方法")
        except Exception as e:
            import traceback
            error_msg = f"OCR识别出错: {str(e)}"
            self.ocr_completed.emit(error_msg)

class ScreenshotWidget(QWidget):
    """截图选择区域窗口"""
    screenshot_completed = pyqtSignal(object)

    def __init__(self, screenshot_np):
        super().__init__()
        self.screenshot_np = screenshot_np
        self.begin = QPoint()
        self.end = QPoint()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.showFullScreen()
        self.setStyleSheet("background-color:black; opacity: 0.5;")
        self.setCursor(Qt.CrossCursor)

        # 将numpy数组转换为QImage
        height, width, channel = screenshot_np.shape
        bytes_per_line = 3 * width
        # 注意：OpenCV使用BGR格式，而Qt使用RGB格式，这里需要转换
        if channel == 3:  # RGB
            qimg = QImage(screenshot_np.data, width, height, bytes_per_line, QImage.Format_RGB888)
        else:  # RGBA
            qimg = QImage(screenshot_np.data, width, height, screenshot_np.strides[0], QImage.Format_RGBA8888)

        # 将QImage转换为QPixmap
        self.pixmap = QPixmap.fromImage(qimg)

    def paintEvent(self, event=None):
        from PyQt5.QtGui import QPainter, QColor
        from PyQt5.QtCore import QRect

        painter = QPainter(self)
        if hasattr(self, 'pixmap') and not self.pixmap.isNull():
            painter.drawPixmap(self.rect(), self.pixmap)

        # 绘制选择区域
        if not self.begin.isNull() and not self.end.isNull():
            rect = QRect(self.begin, self.end)
            painter.setPen(QColor(255, 0, 0))
            painter.drawRect(rect)

            # 半透明填充选择区域外的部分
            mask = QColor(0, 0, 0, 128)
            painter.fillRect(0, 0, self.width(), self.begin.y(), mask)
            painter.fillRect(0, self.end.y(), self.width(), self.height() - self.end.y(), mask)
            painter.fillRect(0, self.begin.y(), self.begin.x(), self.end.y() - self.begin.y(), mask)
            painter.fillRect(self.end.x(), self.begin.y(), self.width() - self.end.x(), self.end.y() - self.begin.y(), mask)

    def mousePressEvent(self, event):
        self.begin = event.pos()
        self.end = event.pos()
        self.update()

    def mouseMoveEvent(self, event):
        self.end = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        self.end = event.pos()
        self.update()

        # 确保选择区域有效
        if self.begin.x() > self.end.x():
            self.begin.setX(self.end.x())
            self.end.setX(self.begin.x())
        if self.begin.y() > self.end.y():
            self.begin.setY(self.end.y())
            self.end.setY(self.begin.y())

        # 获取选择区域的截图
        x = min(self.begin.x(), self.end.x())
        y = min(self.begin.y(), self.end.y())
        width = abs(self.begin.x() - self.end.x())
        height = abs(self.begin.y() - self.end.y())

        if width > 0 and height > 0:
            # 从原始截图中裁剪选择区域
            region = self.screenshot_np[y:y+height, x:x+width]
            # 转换为PIL Image对象
            pil_image = Image.fromarray(region)
            self.screenshot_completed.emit(pil_image)
        else:
            self.screenshot_completed.emit(None)

        self.close()

    def keyPressEvent(self, event):
        # 按ESC取消截图
        if event.key() == Qt.Key_Escape:
            self.screenshot_completed.emit(None)
            self.close()

class TranslatorAPI:
    """翻译API调用类"""

    # 创建一个会话对象以复用连接
    _session = requests.Session()

    @classmethod
    def baidu_translate(cls, text, from_lang="auto", to_lang="zh"):
        """调用百度翻译API"""
        if not text.strip():
            return ""

        app_id = config.BAIDU_APP_ID
        secret_key = config.BAIDU_SECRET_KEY

        if app_id == "YOUR_APP_ID" or secret_key == "YOUR_SECRET_KEY":
            return "请在config.py中配置百度翻译API的APP_ID和SECRET_KEY"

        url = "https://api.fanyi.baidu.com/api/trans/vip/translate"
        salt = str(random.randint(32768, 65536))
        sign = hashlib.md5((app_id + text + salt + secret_key).encode()).hexdigest()

        payload = {
            'appid': app_id,
            'q': text,
            'from': from_lang,
            'to': to_lang,
            'salt': salt,
            'sign': sign
        }

        try:
            # 使用会话对象发送请求，可以复用连接
            response = cls._session.post(url, data=payload, timeout=5)
            result = response.json()

            if "error_code" in result:
                return f"翻译出错: {result['error_code']} - {result.get('error_msg', '未知错误')}"

            if "trans_result" not in result:
                return "翻译响应中缺少翻译结果"

            # 优化字符串拼接
            translated_parts = [item["dst"] for item in result["trans_result"]]
            return "\n".join(translated_parts)

        except requests.exceptions.Timeout:
            return "翻译请求超时，请稍后重试"
        except requests.exceptions.RequestException:
            return "网络请求错误，请检查网络连接"
        except ValueError:
            return "API响应格式错误"
        except Exception:
            return "翻译过程出错，请稍后重试"

class TranslatorApp(QMainWindow):
    """翻译工具主窗口"""

    def __init__(self):
        super().__init__()
        self.initUI()

        # 在初始化完成后调整下拉菜单宽度
        self.adjustComboBoxWidths()

    def handle_ocr_result(self, text):
        """处理OCR识别结果"""
        # 将识别的文本显示在源文本框中
        self.source_text.setText(text)

        # 自动翻译
        if text.strip() and not text.startswith("OCR识别失败") and not text.startswith("请在config.py中配置"):
            self.translate_text()
            self.statusBar().showMessage("OCR识别和翻译完成")
        else:
            self.statusBar().showMessage("OCR识别结果: " + text)
            # 如果识别失败，提示手动输入
            if text.startswith("OCR识别失败") or text.startswith("请在config.py中配置"):
                QMessageBox.information(self, 'OCR识别失败',
                                      f"{text}\n\n您可以手动输入截图中的文字进行翻译。")
                self.source_text.clear()
                self.source_text.setFocus()

    def initUI(self):
        """初始化用户界面"""
        self.setWindowTitle("多功能翻译工具")
        self.setGeometry(100, 100, config.DEFAULT_WIDTH, config.DEFAULT_HEIGHT)

        # 设置应用图标
        try:
            # 尝试多种可能的图标路径
            icon_paths = [
                "ico.ico",  # 当前目录
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "ico.ico"),  # 脚本所在目录
                os.path.join(os.path.dirname(sys.executable), "ico.ico"),  # 可执行文件所在目录
                os.path.join(sys._MEIPASS, "ico.ico") if hasattr(sys, "_MEIPASS") else None  # PyInstaller打包时的临时目录
            ]

            # 尝试每个路径
            app_icon = None
            for path in icon_paths:
                if path and os.path.exists(path):
                    app_icon = QIcon(path)
                    break

            if app_icon:
                self.setWindowIcon(app_icon)
            else:
                print("警告: 无法找到图标文件")
        except Exception as e:
            # 如果图标文件不存在，则忽略错误
            print(f"设置图标出错: {str(e)}")
        # 设置应用样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                background-color: white;
                selection-background-color: #0078d7;
                font-family: 'Microsoft YaHei', Arial, sans-serif;
            }
            QPushButton {
                background-color: #0078d7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 80px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0063b1;
            }
            QPushButton:pressed {
                background-color: #004e8c;
            }
            QComboBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 4px 8px;
                background-color: white;
                min-width: 150px;
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                font-size: 14px;
            }
            QSplitter::handle {
                background-color: #ddd;
            }
            QStatusBar {
                background-color: #f0f0f0;
                color: #555;
            }
        """)

        # 设置中心窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)

        # 顶部控制区域
        control_layout = QHBoxLayout()

        # 源语言选择 - 使用标准下拉菜单
        self.from_lang_combo = QComboBox()

        # 完全清除所有样式
        self.from_lang_combo.setStyleSheet("")

        # 设置固定宽度和高度
        self.from_lang_combo.setFixedWidth(200)
        self.from_lang_combo.setFixedHeight(30)

        # 添加语言选项
        self.from_lang_combo.clear()  # 先清除所有项
        for lang in config.LANGUAGES:
            self.from_lang_combo.addItem(lang)

        # 设置默认选中项
        index = self.from_lang_combo.findText(config.DEFAULT_FROM_LANG)
        if index >= 0:
            self.from_lang_combo.setCurrentIndex(index)

        # 连接信号
        self.from_lang_combo.currentIndexChanged.connect(self.on_language_changed)
        # 设置文本对齐方式 - 不使用可编辑模式
        # self.from_lang_combo.setEditable(True)
        # self.from_lang_combo.lineEdit().setReadOnly(True)
        # self.from_lang_combo.lineEdit().setAlignment(Qt.AlignCenter)

        # 目标语言选择 - 使用标准下拉菜单
        self.to_lang_combo = QComboBox()

        # 完全清除所有样式
        self.to_lang_combo.setStyleSheet("")

        # 设置固定宽度和高度
        self.to_lang_combo.setFixedWidth(200)
        self.to_lang_combo.setFixedHeight(30)

        # 添加语言选项
        self.to_lang_combo.clear()  # 先清除所有项
        for lang in config.LANGUAGES:
            if lang != "自动检测":  # 目标语言不能是自动检测
                self.to_lang_combo.addItem(lang)

        # 设置默认选中项
        index = self.to_lang_combo.findText(config.DEFAULT_TO_LANG)
        if index >= 0:
            self.to_lang_combo.setCurrentIndex(index)

        # 连接信号
        self.to_lang_combo.currentIndexChanged.connect(self.on_language_changed)
        # 设置文本对齐方式 - 不使用可编辑模式
        # self.to_lang_combo.setEditable(True)
        # self.to_lang_combo.lineEdit().setReadOnly(True)
        # self.to_lang_combo.lineEdit().setAlignment(Qt.AlignCenter)

        # 交换语言按钮
        self.swap_btn = QPushButton("⇄")
        self.swap_btn.setToolTip("交换源语言和目标语言")
        self.swap_btn.clicked.connect(self.swap_languages)
        self.swap_btn.setStyleSheet("""
            background-color: #f0f0f0;
            color: #333;
            border-radius: 4px;
            padding: 4px 8px;
            font-weight: bold;
            font-size: 16px;
        """)

        # 截图按钮
        self.screenshot_btn = QPushButton("截图翻译")
        self.screenshot_btn.setToolTip("截取屏幕区域并直接进行文字识别和翻译 (Ctrl+Shift+Alt+Z)")
        self.screenshot_btn.clicked.connect(self.take_screenshot)
        self.screenshot_btn.setStyleSheet("""
            background-color: #28a745;
            color: white;
            font-weight: bold;
        """)

        # 粘贴按钮
        self.paste_btn = QPushButton("粘贴")
        self.paste_btn.setToolTip("从剪贴板粘贴文本")
        self.paste_btn.clicked.connect(self.paste_from_clipboard)
        self.paste_btn.setStyleSheet("""
            background-color: #17a2b8;
            color: white;
        """)

        # 清空按钮
        self.clear_btn = QPushButton("清空")
        self.clear_btn.setToolTip("清空文本框")
        self.clear_btn.clicked.connect(self.clear_text)
        self.clear_btn.setStyleSheet("""
            background-color: #dc3545;
            color: white;
        """)

        # 添加控件到控制布局
        source_lang_label = QLabel("源语言:")
        source_lang_label.setStyleSheet("font-weight: bold; color: #555; font-size: 14px;")
        target_lang_label = QLabel("目标语言:")
        target_lang_label.setStyleSheet("font-weight: bold; color: #555; font-size: 14px;")

        # 创建语言选择布局
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(source_lang_label)
        lang_layout.addWidget(self.from_lang_combo, 1)  # 给予更多的扩展空间
        lang_layout.addWidget(self.swap_btn)
        lang_layout.addWidget(target_lang_label)
        lang_layout.addWidget(self.to_lang_combo, 1)  # 给予更多的扩展空间

        # 创建按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.paste_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.screenshot_btn)

        # 将语言选择布局和按钮布局添加到主控制布局
        control_layout.addLayout(lang_layout, 3)  # 语言选择占据更多空间
        control_layout.addLayout(button_layout, 1)

        # 添加控制布局到主布局
        main_layout.addLayout(control_layout)

        # 创建分割器
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(1)

        # 源文本区域
        self.source_text = QTextEdit()
        self.source_text.setPlaceholderText("在此输入要翻译的文本，或使用粘贴功能...")
        self.source_text.setFont(QFont("Microsoft YaHei", config.DEFAULT_FONT_SIZE))
        self.source_text.textChanged.connect(self.auto_translate)
        # 添加标题标签
        source_label = QLabel("原文")
        source_label.setStyleSheet("""
            font-weight: bold;
            font-size: 14px;
            color: #333;
            margin-bottom: 5px;
        """)

        # 翻译结果区域
        self.result_text = QTextEdit()
        self.result_text.setPlaceholderText("翻译结果将显示在这里...")
        self.result_text.setFont(QFont("Microsoft YaHei", config.DEFAULT_FONT_SIZE))
        self.result_text.setReadOnly(True)
        # 添加标题标签
        result_label = QLabel("译文")
        result_label.setStyleSheet("""
            font-weight: bold;
            font-size: 14px;
            color: #333;
            margin-bottom: 5px;
        """)

        # 创建源文本容器
        source_container = QWidget()
        source_layout = QVBoxLayout(source_container)
        source_layout.addWidget(source_label)
        source_layout.addWidget(self.source_text)
        source_layout.setContentsMargins(0, 0, 0, 10)

        # 创建翻译结果容器
        result_container = QWidget()
        result_layout = QVBoxLayout(result_container)
        result_layout.addWidget(result_label)
        result_layout.addWidget(self.result_text)
        result_layout.setContentsMargins(0, 0, 0, 0)

        # 添加容器到分割器
        splitter.addWidget(source_container)
        splitter.addWidget(result_container)

        # 设置分割器的初始大小
        splitter.setSizes([int(config.DEFAULT_HEIGHT * 0.4), int(config.DEFAULT_HEIGHT * 0.6)])

        # 添加分割器到主布局
        main_layout.addWidget(splitter)

        # 底部状态栏
        status_bar = self.statusBar()
        status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #f8f9fa;
                color: #555;
                border-top: 1px solid #ddd;
                padding: 3px;
                font-size: 12px;
            }
        """)
        status_bar.showMessage("就绪")

        # 设置快捷键
        # 使用数字键码方式设置快捷键，避免字符串解析问题
        # Ctrl(4194368) + Shift(4194368) + Alt(4194304) + Z(90)
        self.shortcut_screenshot = QShortcut(QKeySequence(Qt.ControlModifier | Qt.ShiftModifier | Qt.AltModifier | Qt.Key_Z), self)
        self.shortcut_screenshot.activated.connect(self.take_screenshot)

        # 注册全局热键
        try:
            keyboard.add_hotkey('ctrl+shift+alt+z', self.take_screenshot)
        except Exception:
            pass

        self.shortcut_paste = QShortcut(QKeySequence("Ctrl+V"), self)
        self.shortcut_paste.activated.connect(self.paste_from_clipboard)

        self.shortcut_copy = QShortcut(QKeySequence("Ctrl+C"), self)
        self.shortcut_copy.activated.connect(self.copy_to_clipboard)

        # 初始化截图线程
        self.screenshot_thread = None


    def swap_languages(self):
        """交换源语言和目标语言"""
        # 阻止所有可能触发翻译的信号
        self.blockSignals(True)
        self.from_lang_combo.blockSignals(True)
        self.to_lang_combo.blockSignals(True)
        self.source_text.blockSignals(True)

        try:
            # 获取当前语言
            from_lang = self.from_lang_combo.currentText()
            to_lang = self.to_lang_combo.currentText()

            # 获取当前文本
            current_text = self.source_text.toPlainText().strip()
            current_result = self.result_text.toPlainText().strip()

            # 自动检测不能作为目标语言
            if from_lang == "自动检测":
                # 如果源语言是自动检测，只将目标语言设为源语言
                self.from_lang_combo.setCurrentText(to_lang)
                self.statusBar().showMessage("目标语言不能设为'自动检测'")
            else:
                # 正常交换语言
                self.to_lang_combo.setCurrentText(from_lang)
                self.from_lang_combo.setCurrentText(to_lang)

            # 交换文本
            if current_text and current_result:
                self.source_text.setText(current_result)
                self.result_text.clear()
        finally:
            # 恢复信号
            self.source_text.blockSignals(False)
            self.to_lang_combo.blockSignals(False)
            self.from_lang_combo.blockSignals(False)
            self.blockSignals(False)

        # 使用QTimer延迟翻译，避免UI冻结
        if self.source_text.toPlainText().strip():
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, self.translate_text)

    def take_screenshot(self):
        """截图功能"""
        # 检查是否有正在运行的截图线程
        if hasattr(self, 'screenshot_thread') and self.screenshot_thread is not None and self.screenshot_thread.isRunning():
            return

        self.setWindowState(Qt.WindowMinimized)
        self.statusBar().showMessage("正在准备截图...")

        # 创建并启动截图线程
        self.screenshot_thread = ScreenshotThread()
        self.screenshot_thread.screenshot_taken.connect(self.process_screenshot)
        self.screenshot_thread.finished.connect(self.on_screenshot_thread_finished)
        self.screenshot_thread.start()

    def on_screenshot_thread_finished(self):
        """截图线程完成时的处理"""
        # 断开信号连接，避免内存泄漏
        if hasattr(self, 'screenshot_thread') and self.screenshot_thread is not None:
            self.screenshot_thread.screenshot_taken.disconnect()
            self.screenshot_thread.finished.disconnect()
            self.screenshot_thread = None

    def process_screenshot(self, screenshot):
        """处理截图"""
        if screenshot is not None:
            try:
                # 创建截图选择窗口
                self.screenshot_widget = ScreenshotWidget(screenshot)
                self.screenshot_widget.screenshot_completed.connect(self.process_selected_area)
                self.screenshot_widget.show()
            except Exception as e:
                self.statusBar().showMessage(f"截图处理出错: {str(e)}")
                self.setWindowState(Qt.WindowActive)
        else:
            self.statusBar().showMessage("截图失败")
            self.setWindowState(Qt.WindowActive)

    def ocr_with_baidu_api(self, image):
        """使用百度OCR API识别图片中的文字"""
        self.statusBar().showMessage("正在进行OCR识别，请稍候...")
        QApplication.processEvents()

        # 百度OCR API配置
        api_key = config.BAIDU_OCR_API_KEY
        secret_key = config.BAIDU_OCR_SECRET_KEY



        # 如果没有配置API密钥，返回提示信息
        if api_key == "YOUR_OCR_API_KEY" or secret_key == "YOUR_OCR_SECRET_KEY":
            error_msg = "请在config.py中配置百度OCR API的API_KEY和SECRET_KEY"
            return error_msg

        try:
            # 获取access_token
            token_url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
            response = requests.get(token_url)
            response_json = response.json()

            access_token = response_json.get("access_token")

            if not access_token:
                error_msg = f"OCR认证失败: {response_json}"
                return error_msg



            # 调用通用文字识别API
            ocr_url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token={access_token}"

            # 将PIL图像转换为二进制数据
            import io
            img_byte_arr = io.BytesIO()

            # 检查图像是否为空
            if image is None:
                return "图像为空，无法进行OCR识别"



            try:
                # 尝试保存图像
                image.save(img_byte_arr, format='PNG')
                img_data = img_byte_arr.getvalue()
                img = base64.b64encode(img_data)
            except Exception as save_error:
                return f"OCR处理图像出错: {str(save_error)}"

            params = {"image": img}
            headers = {'content-type': 'application/x-www-form-urlencoded'}

            response = requests.post(ocr_url, data=params, headers=headers)
            result = response.json()

            # 提取文本
            if "words_result" in result:
                text = ""
                for item in result["words_result"]:
                    text += item["words"] + "\n"
                return text.strip()
            else:
                error_msg = f"OCR识别失败: {result.get('error_msg', '未知错误')}"
                return error_msg
        except Exception as e:
            error_msg = f"OCR API调用出错: {str(e)}"
            return error_msg

    def process_selected_area(self, image):
        """处理选择的截图区域并进行翻译，不保存到本地"""
        self.setWindowState(Qt.WindowActive)

        if image:
            try:
                # 复制到剪贴板
                clipboard = QApplication.clipboard()
                # 将PIL图像转换为QPixmap
                img_array = np.array(image)
                height, width, channel = img_array.shape
                bytes_per_line = 3 * width
                if channel == 3:  # RGB
                    qimg = QImage(img_array.data, width, height, bytes_per_line, QImage.Format_RGB888)
                else:  # RGBA
                    qimg = QImage(img_array.data, width, height, img_array.strides[0], QImage.Format_RGBA8888)
                clipboard.setPixmap(QPixmap.fromImage(qimg))

                self.statusBar().showMessage("截图已复制到剪贴板")

                # 使用百度OCR API识别文字
                self.statusBar().showMessage("截图已复制到剪贴板，正在进行OCR识别...")

                # 检查是否有正在运行的OCR线程
                if hasattr(self, 'ocr_thread') and self.ocr_thread is not None and self.ocr_thread.isRunning():
                    # 如果有正在运行的OCR线程，先断开连接并等待其结束
                    try:
                        self.ocr_thread.ocr_completed.disconnect()
                        self.ocr_thread.wait()
                    except Exception:
                        pass

                # 创建OCR线程，避免阻塞主线程
                self.ocr_thread = OCRThread(image, self)
                self.ocr_thread.ocr_completed.connect(self.handle_ocr_result)
                self.ocr_thread.finished.connect(self.on_ocr_thread_finished)
                self.ocr_thread.start()

                # 显示等待提示
                self.source_text.setText("正在识别文字，请稍候...")
            except Exception as e:
                error_msg = f"处理截图出错: {str(e)}"
                self.statusBar().showMessage(error_msg)

                # 显示错误对话框
                QMessageBox.critical(self, "截图处理错误",
                                    f"处理截图时出错: {str(e)}")
        else:
            self.statusBar().showMessage("已取消截图")

    def on_ocr_thread_finished(self):
        """当OCR线程完成时清理资源"""
        if hasattr(self, 'ocr_thread') and self.ocr_thread is not None:
            try:
                self.ocr_thread.ocr_completed.disconnect()
                self.ocr_thread.finished.disconnect()
            except Exception:
                pass
            self.ocr_thread = None
        else:
            pass

    def paste_from_clipboard(self):
        """从剪贴板粘贴文本"""
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()

        if mime_data.hasText():
            text = clipboard.text()
            if text:
                # 如果当前有选中的文本，则替换选中的文本
                cursor = self.source_text.textCursor()
                if cursor.hasSelection():
                    cursor.insertText(text)
                else:
                    # 否则在当前光标位置插入文本
                    self.source_text.insertPlainText(text)
                self.statusBar().showMessage("已从剪贴板粘贴文本")
            else:
                self.statusBar().showMessage("剪贴板中没有文本")
        else:
            self.statusBar().showMessage("剪贴板中没有可粘贴的文本")

    def copy_to_clipboard(self):
        """复制文本到剪贴板"""
        # 如果结果文本框有焦点，复制结果文本
        if self.result_text.hasFocus():
            text = self.result_text.toPlainText()
            if text:
                clipboard = QApplication.clipboard()
                clipboard.setText(text)
                self.statusBar().showMessage("翻译结果已复制到剪贴板")
        # 否则使用默认的复制行为
        else:
            focused_widget = QApplication.focusWidget()
            if hasattr(focused_widget, 'copy'):
                focused_widget.copy()

    def clear_text(self):
        """清空文本框"""
        self.source_text.clear()
        self.result_text.clear()
        self.statusBar().showMessage("已清空文本")

    # 上次翻译的时间
    _last_translate_time = 0

    def auto_translate(self):
        """自动翻译（当源文本变化时）"""
        import time

        text = self.source_text.toPlainText().strip()

        # 如果文本为空，清空结果
        if not text:
            self.result_text.clear()
            return

        # 获取当前时间
        current_time = time.time()

        # 根据文本长度决定防抖动时间
        if len(text) < 50:  # 很短的文本立即翻译
            debounce_time = 0
        elif len(text) < 200:  # 中等长度的文本等待300毫秒
            debounce_time = 0.3
        else:  # 长文本等待800毫秒
            debounce_time = 0.8

        # 如果距离上次翻译的时间足够长，则翻译
        if current_time - self._last_translate_time > debounce_time:
            self._last_translate_time = current_time
            self.translate_text()

    def on_language_changed(self, _):
        """当语言选择变化时触发翻译"""
        if self.source_text.toPlainText().strip():
            self.translate_text()

    def adjustComboBoxWidths(self):
        """调整下拉菜单的宽度以适应最长的选项"""
        # 不需要额外调整，因为我们已经设置了固定宽度
        pass

    # 翻译缓存字典
    _translation_cache = {}

    def translate_text(self):
        """翻译文本"""
        text = self.source_text.toPlainText().strip()
        if not text:
            return

        # 获取语言代码
        try:
            from_lang = config.LANGUAGES[self.from_lang_combo.currentText()]
            to_lang = config.LANGUAGES[self.to_lang_combo.currentText()]
        except KeyError:
            self.statusBar().showMessage("语言选择错误")
            return

        # 检查缓存
        cache_key = f"{text}|{from_lang}|{to_lang}"
        if cache_key in self._translation_cache:
            self.result_text.setText(self._translation_cache[cache_key])
            self.statusBar().showMessage("翻译完成 (从缓存)")
            return

        # 更新状态栏
        self.statusBar().showMessage("正在翻译...")

        try:
            # 调用翻译API
            translated_text = TranslatorAPI.baidu_translate(text, from_lang, to_lang)

            # 检查错误
            if any(translated_text.startswith(err) for err in [
                "翻译出错", "网络请求错误",
                "API响应格式错误", "翻译过程出错"]):
                self.statusBar().showMessage(translated_text)
                return

            # 更新结果和缓存
            self.result_text.setText(translated_text)
            self._translation_cache[cache_key] = translated_text

            # 限制缓存大小
            if len(self._translation_cache) > 100:
                # 删除最早的缓存项
                self._translation_cache.pop(next(iter(self._translation_cache)))

            self.statusBar().showMessage("翻译完成")

        except Exception as e:
            self.statusBar().showMessage(f"翻译错误: {str(e)}")

def show_debug_info():
    """显示调试信息"""
    debug_info = [
        f"Python版本: {sys.version}",
        f"OS类型: {os.name}",
        f"PIL版本: {Image.__version__ if hasattr(Image, '__version__') else '未知'}",
        f"PyQt5版本: {Qt.QT_VERSION_STR if hasattr(Qt, 'QT_VERSION_STR') else '未知'}",
        f"NumPy版本: {np.__version__ if hasattr(np, '__version__') else '未知'}"
    ]
    return "\n".join(debug_info)

def main():
    """主函数"""
    try:
        # 强制禁用所有日志和警告
        import logging

        # 将所有日志级别设置为CRITICAL，只显示最严重的错误
        logging.basicConfig(level=logging.CRITICAL)

        # 特别禁用PIL的日志
        logging.getLogger('PIL').setLevel(logging.CRITICAL)
        logging.getLogger('PIL.PngImagePlugin').setLevel(logging.CRITICAL)

        # 禁用Qt的警告
        os.environ['QT_LOGGING_RULES'] = '*.debug=false;*.warning=false;*.critical=false'

        # 初始化应用
        debug_info = show_debug_info()
        app = QApplication(sys.argv)

        # 在应用程序级别设置图标
        try:
            from PyQt5.QtGui import QIcon

            # 尝试多种可能的图标路径
            icon_paths = [
                "ico.ico",  # 当前目录
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "ico.ico"),  # 脚本所在目录
                os.path.join(os.path.dirname(sys.executable), "ico.ico"),  # 可执行文件所在目录
                os.path.join(sys._MEIPASS, "ico.ico") if hasattr(sys, "_MEIPASS") else None  # PyInstaller打包时的临时目录
            ]

            # 尝试每个路径
            app_icon = None
            for path in icon_paths:
                if path and os.path.exists(path):
                    app_icon = QIcon(path)
                    print(f"找到图标文件: {path}")
                    break

            if app_icon:
                app.setWindowIcon(app_icon)
            else:
                print("警告: 无法找到图标文件")
        except Exception as e:
            print(f"设置应用图标出错: {str(e)}")

        # 禁用Qt的警告输出
        app.setQuitOnLastWindowClosed(True)

        translator = TranslatorApp()
        translator.show()

        # 不需要恢复标准错误输出
        pass

        sys.exit(app.exec_())
    except Exception as e:
        # 显示错误对话框
        error_msg = f"程序发生错误: {str(e)}\n\n调试信息:\n{debug_info if 'debug_info' in locals() else ''}"
        if QApplication.instance():
            QMessageBox.critical(None, "错误", error_msg)
        else:
            app = QApplication(sys.argv)
            QMessageBox.critical(None, "错误", error_msg)
            sys.exit(1)

if __name__ == "__main__":
    main()
