import re
from collections import namedtuple
import Pylogger

logger = Pylogger.get_logger()
Pylogger.logger_enable()  # 啟用日誌記錄

Token = namedtuple('Token', ['type', 'value', 'line', 'column'])

class Lexer:
    def __init__(self, text):
        self.text = text

        self.keywords = {
            'CUE', 'IN', 'FUNC', 'INTERVAL', 'DIMMER', 'COLOR',
            'STROBE', 'OTHERS', 'START', 'END', 'VALUE', 'FROM', 'TO',
            'SETTING', 'PLAYBACK', 'SHOW', 'WAIT',
            # 其他你需要的關鍵字
        }
        self.token_specification = [
            ('NUMBER',   r'\d+(\.\d*)?'),
            ('ID',       r'[A-Za-z_]\w*'),
            ('OP',       r'[+\-*/=]'),
            ('DOT',      r'\.'),
            ('COLON',    r':'),
            ('LBRACE',   r'\{'),
            ('RBRACE',   r'\}'),
            ('LSQUARE',  r'\['),
            ('RSQUARE',  r'\]'),
            ('COMMA',    r','),
            ('LPAREN',   r'\('),
            ('RPAREN',   r'\)'),
            ('STRING',   r'"[^"]*"'),
            ('NEWLINE',  r'\n'),
            ('SKIP',     r'[ \t]+'),
            ('COMMENT',  r'#.*'),
            ('MISMATCH', r'.'),
        ]
        self.token_regex = re.compile('|'.join(
            f'(?P<{name}>{pattern})' for name, pattern in self.token_specification
        ))
        self.line = 1
        self.column = 1
        self.keep_newline = False
        self._recent_tokens = []

    def _last_tokens_look_like_interval(self):
        tokens = self._recent_tokens
        # 期望格式： INTERVAL LSQUARE NUMBER (OP '-')? NUMBER? RSQUARE LBRACE
        # 最簡格式長度至少 7，複雜格式長度至少 7
        try:
            # 從最後往前檢查
            # 簡化以最後6個token為例
            last = tokens[-7:] if len(tokens) >= 7 else tokens[:]
            logger.lexer(f"Last tokens: {last}")
            # 先找 INTERVAL token
            interval_pos = None
            for i, t in enumerate(last):
                if t.type == 'INTERVAL':
                    logger.lexer(f"Found INTERVAL at position {i}")
                    interval_pos = i
                    break
            if interval_pos is None:
                return False
            # 接著判斷模式
            # 期待 INTERVAL後面是 LSQUARE、NUMBER、可能OP、NUMBER、RSQUARE
            idx = interval_pos
            if len(last) < idx + 5:
                logger.lexer("Not enough tokens after INTERVAL")
                return False
            if last[idx + 1].type != 'LSQUARE':
                logger.lexer(f"Expected LSQUARE after INTERVAL but found {last[idx + 1].type}")
                return False
            if last[idx + 2].type != 'NUMBER':
                logger.lexer(f"Expected NUMBER after LSQUARE but found {last[idx + 2].type}")
                return False
            # 判斷是否有範圍
            if len(last) > idx + 5 and last[idx + 3].type == 'OP' and last[idx + 3].value == '-':
                logger.lexer(f"Found range in INTERVAL at position {idx + 3}")
                if len(last) < idx + 7:
                    logger.lexer("Not enough tokens for range in INTERVAL")
                    return False
                if last[idx + 4].type != 'NUMBER':
                    logger.lexer(f"Expected NUMBER after '-' but found {last[idx + 4].type}")
                    return False
                if last[idx + 5].type != 'RSQUARE':
                    logger.lexer(f"Expected RSQUARE after range but found {last[idx + 5].type}")
                    return False
                logger.lexer("Found INTERVAL with range")
                logger.lex_info("Start generating NEWLINE tokens")
                return True
            else:
                # 沒有範圍，檢查第四個是不是 RSQUARE
                if last[idx + 3].type == 'RSQUARE':
                    logger.lexer("Found simple INTERVAL without range")
                    logger.lex_info("Start generating NEWLINE tokens")
                    return True
            return False
        except IndexError:
            logger.lexer("IndexError in function _last_tokens_look_like_interval")
            return False

    def generate_tokens(self):
        self._recent_tokens = []
        for mo in self.token_regex.finditer(self.text):
            kind = mo.lastgroup
            value = mo.group()

            # 更新行列計數
            if kind == 'NEWLINE':
                self.line += 1
                self.column = 1
                # 根據狀態決定是否產生 NEWLINE token
                if self.keep_newline:
                    token = Token(kind, value, self.line, self.column)
                    logger.gene(f'\tGenerated token: {token}')
                    self._recent_tokens.append(token)
                    yield token
                continue

            elif kind == 'SKIP' or kind == 'COMMENT':
                logger.lexer(f'Skipping {kind} token: {value!r}')
                self.column += len(value)
                continue

            elif kind == 'MISMATCH':
                logger.error(f'Unexpected character {value!r} at line {self.line}, column {self.column}')
                raise RuntimeError(f'Unexpected character {value!r} at line {self.line} column {self.column}')

            else:
                # 關鍵字轉換
                if kind == 'ID' and value.upper() in self.keywords:
                    logger.lexer(f'Converting keyword {value!r} to uppercase')
                    kind = value.upper()

                token = Token(kind, value, self.line, self.column)
                logger.gene(f'\tGenerated token: {token}')
                self._recent_tokens.append(token)
                if len(self._recent_tokens) > 10:
                    self._recent_tokens.pop(0)

                # 進入 INTERVAL[...] 區塊時開啟 keep_newline
                if kind == 'LBRACE':
                    logger.lexer(f'Enter block with LBRACE,detecting INTERVAL-like structure')
                    if self._last_tokens_look_like_interval():
                        self.keep_newline = True

                # 離開區塊時關閉 keep_newline
                if kind == 'RBRACE':
                    # 簡單判斷是否還有未閉合大括號
                    logger.lexer(f'Detected RBRACE,detecting left braces')
                    if not any(t.type == 'LBRACE' for t in self._recent_tokens):
                        logger.lexer(f'No more LBRACE tokens, setting keep_newline to False')
                        self.keep_newline = False
                    else:
                        logger.lexer(f'Still have LBRACE tokens, keeping keep_newline True')
                yield token
                self.column += len(value)

if __name__ == "__main__":
    sample_text = '''
CUE cross_back_01 START
    # input BPM, BPM scale rate, lights
    IN BPM, RATE, LIGHT

    # create functions
    FUNC wave2(x) = 1-sin(x)

    # declare the number of INTERVAL, initially defined INTERVAL=1/(BPM*RATE)s
    # so for a 4/4 music with 60 beats/min implies when BPM = 60 and RATE = 2
    # an INTERVAL = the length of an eighth note
    # and a bar have 8 INTERVALs
    INTERVAL 4

    # DIMMER setting in INTERVAL[1-4] with gradually change in the value of two waves
    # LIGHT.L would take the left 1/2 of the light array
    # LIGHT.R would take another 1/2 of the light array
    # LIGHT.ALL would take all lights in the light array
    DIMMER{
        INTERVAL[1-4]{
            LIGHT.L DIMMER func wave1 from 0 to PI
            LIGHT.R DIMMER func wave2 from 0 to PI
        }
    }

    # COLOR setting in 4 INTERVALs
    COLOR{
        INTERVAL[1]{
            LIGHT.L COLOR value "red_a"
            LIGHT.R COLOR value "blue_a"
        }
        INTERVAL[2]{
            LIGHT.L COLOR value "blue_a"
            LIGHT.R COLOR value "red_a"
        }
        INTERVAL[3-4]{
            LIGHT.ALL COLOR value "green_a"
        }
    }

    # STROBE settings
    STROBE{
        INTERVAL[1-2]{
            LIGHT.ALL STROBE value 0
        }
        INTERVAL[3-4]{
            LIGHT.R STROBE value 255
        }
    }

    # OTHERS deal with other unused parameter of all lights
    # {bypass} means keep the previous values
    # {off} means set all the parameters with minimum value
    # {full} means set all the parameters with maximum value
    OTHERS{bypass}

CUE END
    '''

    lexer = Lexer(sample_text)
    for token in lexer.generate_tokens():
        print(token)