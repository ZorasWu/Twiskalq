import logging
import os
import sys
import datetime

_enable_logging = False
_my_logger = logging.getLogger("logger")
_my_logger.setLevel(logging.DEBUG)

Levels = {
    #NOTSET: 0,  # 預設等級，未設定時使用
    #DEBUG: 10,  # 用於詳細的除錯資訊
    #INFO: 20,   # 用於一般資訊性訊息
    #WARNING: 30,  # 用於警告訊息
    #ERROR: 40,  # 用於錯誤訊息
    #CRITICAL: 50,  # 用於嚴重錯誤訊息
    "LEXER": 1,
    "GENE": 2,
    "LEX_INFO": 3,
    "CUE_PARSER": 4,
    "CONS": 5,
    "SHOW_PARSER": 6,

}


def add_custom_log_levels(levels_dict):
    for name, level_num in levels_dict.items():
        # 註冊等級名稱
        logging.addLevelName(level_num, name)

        # 定義函式，捕捉 name, level_num 當前值避免閉包問題
        def log_for_level(self, message, *args, __level_num=level_num, **kws):
            if self.isEnabledFor(__level_num):
                kws['stacklevel'] = kws.get('stacklevel', 20)
                self._log(__level_num, message, args, **kws)

        # 把函式名稱設成小寫等級名
        func_name = name.lower()
        setattr(logging.Logger, func_name, log_for_level)

def get_default_log_file():
    # 取得主執行檔完整路徑
    # sys.argv[0] 是執行的腳本路徑，若用 __file__ 會是模組本身路徑
    script_path = sys.argv[0]
    base_name = os.path.basename(script_path)           # 例如 main.py
    name_without_ext = os.path.splitext(base_name)[0]   # 取掉副檔名，例如 main
    log_file_name = f"{name_without_ext}_run.log"       # 拼成 main_run.log
    return log_file_name

def logger_enable(log_file_path=None):
    add_custom_log_levels(Levels)
    global _enable_logging
    if not _enable_logging:
        if log_file_path is None:
            log_file_path = get_default_log_file()
        file_handler = logging.FileHandler(log_file_path,mode='w',encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(levelname)-8s - %(message)s - from %(funcName)s:%(lineno)d')
        file_handler.setFormatter(formatter)
        _my_logger.addHandler(file_handler)
        _enable_logging = True
        print(f"Logging enabled, writing to {log_file_path}")
        print("Logging starts at", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f"))

def logger_disable():
    global _enable_logging
    if _enable_logging:
        for handler in _my_logger.handlers[:]:
            _my_logger.removeHandler(handler)
            handler.close()
        _enable_logging = False
        print("Logging disabled")
        print("Logging stops at", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f"))


def get_logger():
    return _my_logger

if __name__ == "__main__":
    # 測試日誌功能
    
    logger = get_logger()
    logger_enable()
    logger.info("This is an info message.")
    logger.debug("This is a debug message.")
    logger.error("This is an error message.")
    logger.cons("This is a consumer message.")
    logger_disable()  # 停止日誌記錄