"""
配置文件，存储翻译API的密钥和其他设置
"""

# 百度翻译API配置
# 请替换为您自己的APP ID和密钥
BAIDU_APP_ID = ""
BAIDU_SECRET_KEY = ""

# 百度OCR API配置
# 请替换为您自己的API密钥
# 注意：这里需要使用百度AI平台的API Key和Secret Key，不是翻译API的密钥
BAIDU_OCR_API_KEY = ""
BAIDU_OCR_SECRET_KEY = ""

# 有道翻译API配置（备选）
YOUDAO_APP_KEY = "YOUR_APP_KEY"
YOUDAO_APP_SECRET = "YOUR_APP_SECRET"




# 界面设置
DEFAULT_WIDTH = 800
DEFAULT_HEIGHT = 600
DEFAULT_FONT_SIZE = 12

# 语言设置
LANGUAGES = {
    "自动检测": "auto",
    "中文": "zh",
    "英语": "en",
    "日语": "jp",
    "韩语": "kor",
    "法语": "fra",
    "西班牙语": "spa",
    "俄语": "ru",
    "德语": "de",
    "意大利语": "it",
    "葡萄牙语": "pt"
}

# 默认语言设置
DEFAULT_FROM_LANG = "自动检测"
DEFAULT_TO_LANG = "中文"
