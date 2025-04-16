# 多功能翻译工具

一个基于Python开发的可视化翻译工具，支持文本输入翻译和截图翻译功能，使用百度OCR API进行文字识别，适合打包为exe文件。

## 功能特点

- 支持文本输入翻译：手动输入或粘贴文本进行翻译
- 支持截图翻译功能：截取屏幕区域并自动OCR识别翻译
- 支持多种语言：中文、英语、日语、韩语等多种语言互译
- 简洁美观的用户界面：基于PyQt5开发的现代化界面
- 快捷键支持：使用Ctrl+Shift+Alt+Z快速截图，Ctrl+V粘贴文本
- 使用在线OCR API：无需包含OCR引擎，打包体积小

## 安装说明

### 1. 安装依赖库

```bash
pip3 install -r requirements.txt
```

### 2. 配置API

1. 注册[百度翻译开放平台](https://fanyi-api.baidu.com/)账号
   - 创建应用获取翻译API的APP ID和密钥
   - 在`config.py`中填入您的BAIDU_APP_ID和BAIDU_SECRET_KEY

2. 注册[百度AI开放平台](https://ai.baidu.com/)账号
   - 创建文字识别应用获取OCR API的API Key和Secret Key
   - 在`config.py`中填入您的BAIDU_OCR_API_KEY和BAIDU_OCR_SECRET_KEY

## 使用方法

1. 运行程序：
```bash
python translator.py
```

2. 文本输入翻译：
   - 在上方文本框中输入要翻译的文字
   - 程序会自动翻译并在下方显示结果
   - 也可以点击"粘贴"按钮或使用Ctrl+V从剪贴板粘贴文本

3. 截图翻译功能：
   - 点击"截图翻译"按钮或按下Ctrl+Shift+Alt+Z
   - 选择屏幕上的区域
   - 程序会自动复制截图到剪贴板
   - 程序会使用百度OCR API直接识别截图中的文字并翻译
   - 如果OCR识别失败，可以手动输入文字进行翻译

4. 语言设置：
   - 从下拉菜单中选择源语言和目标语言
   - 点击中间的交换按钮可以快速交换源语言和目标语言

## 打包为exe文件

可以使用PyInstaller打包为独立的exe文件：

```bash
pip3 install pyinstaller
pyinstaller --onefile --windowed --icon=ico.ico translator.py
```

打包后的exe文件将位于`dist`文件夹中。

## 系统要求

- Python 3.6+
- Windows/macOS/Linux

## 常见问题

1. **翻译API调用失败？**
   - 检查网络连接
   - 确认翻译API密钥配置正确
   - 检查API调用次数是否超出限制

2. **OCR识别失败？**
   - 确认OCR API密钥配置正确
   - 检查网络连接
   - 确保截图清晰可读
   - 可以尝试手动输入文字

3. **截图功能不正常？**
   - 确保程序有足够的权限访问屏幕
   - 检查screenshots文件夹是否存在并可写

4. **程序启动失败？**
   - 确保所有依赖库安装正确
   - 检查配置文件是否存在且格式正确

## 许可证

MIT License

