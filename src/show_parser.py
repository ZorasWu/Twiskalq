from cue_parser import CueParser
import Pylogger

logger = Pylogger.get_logger()
Pylogger.logger_enable()  # 啟用日誌記錄
enable_lexer_log = True  # 啟用 Lexer 日誌記錄
enable_cue_log = False  # 啟用 Cue 日誌記錄

if not enable_cue_log:
    logger.setLevel(Pylogger.Levels['SHOW_PARSER'])
elif not enable_lexer_log:
    logger.setLevel(Pylogger.Levels['CUE_PARSER'])
else:
    logger.setLevel(Pylogger.Levels['LEXER'])

class ShowParser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current_token(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self, expected_type=None, expected_value=None):
        token = self.current_token()
        if token.type == 'NEWLINE':
            logger.show_cons(f"\t\t\t Consume ('NEWLINE','\\n') at pos {self.pos}")
        else:
            logger.show_cons(f"\t\t\t Consume ('{token.type}','{token.value}') at pos {self.pos}")
        if not token:
            logger.error("Unexpected end of input")
            raise ValueError("Unexpected end of input")
        if expected_type and token.type != expected_type:
            logger.error(f"Expected {expected_type} but got {token.type} at line {token.line} , column {token.column} , column {token.column}")
            raise ValueError(f"Expected {expected_type} but got {token.type} at line {token.line} , column {token.column} , column {token.column}")
        if expected_value and token.value != expected_value:
            logger.error(f"Expected {expected_value} but got {token.value} at line {token.line} , column {token.column} , column {token.column}")
            raise ValueError(f"Expected {expected_value} but got {token.value} at line {token.line} , column {token.column} , column {token.column}")
        self.pos += 1
        return token

    def parse(self):
        result = {
            "SETTING": None,
            "PLAYBACK": None,
            "SHOWS": []
        }
        while True:
            token = self.current_token()
            if token is None:
                break
            if token.type == 'SETTING':
                result['SETTING'] = self.parse_setting()
            elif token.type == 'PLAYBACK':
                result['PLAYBACK'] = self.parse_playback()
            elif token.type == 'SHOW':
                show = self.parse_show_block()
                result['SHOWS'].append(show)
            else:
                raise ValueError(f"Unexpected token {token.type} at line {token.line} , column {token.column}")
        return result

    def parse_setting(self):
        logger.info("Parsing 'SETTING' block")
        self.consume('SETTING')
        token = self.consume('STRING')
        logger.info("End of 'SETTING' block")
        return token.value.strip('"')

    def parse_playback(self):
        logger.info("Parsing 'PLAYBACK' block")
        self.consume('PLAYBACK')
        token = self.consume('STRING')
        logger.info("End of 'PLAYBACK' block")
        return token.value.strip('"')

    def parse_show_block(self):
        logger.info("Parsing 'SHOW' block")
        self.consume('SHOW')
        number = int(self.consume('NUMBER').value)
        self.consume('START')
        body = self.parse_show_body()
        self.consume('SHOW')
        self.consume('END')
        logger.info("End of 'SHOW' block")
        return {'number': number, 'body': body}

    def parse_show_body(self):
        logger.info("Parsing 'SHOW' body")
        commands = []
        while True:
            token = self.current_token()
            if token is None:
                break
            if token.type == 'SHOW' and self.tokens[self.pos + 1].type == 'END':
                logger.info("End of 'SHOW' body")
                break
            if token.type == 'CUE':
                logger.info("detect 'CUE' command")
                cue_call = self.parse_cue_call()
                commands.append({'type': 'CUE', 'data': cue_call})
            elif token.type == 'WAIT':
                logger.info("detect 'WAIT' command")
                wait_cmd = self.parse_wait()
                commands.append({'type': 'WAIT', 'data': wait_cmd})
            elif token.type == 'COMMENT':
                logger.info(f"Skipping comment: {token.value}")
                self.consume('COMMENT')  # skip comment
            else:
                logger.error(f"Unexpected token {token.type} at line {token.line} , column {token.column}")
                raise ValueError(f"Unexpected token {token.type} at line {token.line} , column {token.column}")
        return commands

    def parse_cue_call(self):
        logger.info("Parsing 'CUE' call")
        self.consume('CUE')
        token = self.current_token()
        if token.type == 'LBRACE':
            # inline cue，呼叫 parse_inline_cue
            # 注意要調整 pos，讓 CueParser 從 'CUE' token 開始解析
            # 先退回一格回到 'CUE'，給 CueParser 完整 Token
            self.pos -= 1
            inline_tokens = self.tokens[self.pos:]  # 從此開始的所有 token
            logger.info("Parsing inline 'CUE' block")
            cue_parser = CueParser(inline_tokens)
            cue_ast = cue_parser.parse(inline=True)
            # 解析完後調整 ShowParser pos 到 CueParser 結束位置
            self.pos += cue_parser.pos
            print(cue_ast,"\n\n\n")
            logger.info("End of inline 'CUE' block")
            logger.info("Cue AST: %s", cue_ast)
            return cue_ast
        else:
            logger.info("Parsing 'CUE' call")
            cue_name = self.consume('ID').value
            params = None
            if self.current_token() and self.current_token().type == 'LPAREN':
                params = self.parse_cue_params()
            body = None
            self.consume('CUE')
            self.consume('END')
            logger.info("End of 'CUE' call")
            return {'name': cue_name, 'params': params, 'body': body}

    def parse_identifier(self):
        # 解析類似 FACE.ALL、LIGHT.L 等帶點的名稱
        logger.info("Parsing identifier")
        token = self.consume('ID')
        name = token.value
        while self.current_token() and self.current_token().type == 'DOT':
            self.consume('DOT')
            next_id = self.consume('ID')
            name += '.' + next_id.value
        logger.info(f"Parsed identifier: {name}")
        return name

    def parse_cue_params(self):
        logger.info("Parsing 'CUE' parameters")
        self.consume('LPAREN')
        params = []
        # 先檢查是否直接是右括號，表示空參數
        if self.current_token() and self.current_token().type == 'RPAREN':
            logger.info("Empty parameters detected")
            self.consume('RPAREN')
            return params  # 空列表

        while True:
            token = self.current_token()
            if token.type == 'ID':
                next_token = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
                if next_token and next_token.type == 'OP' and next_token.value == '=':
                    key = self.parse_identifier()
                    self.consume('OP', '=')
                    value_token = self.current_token()
                    if value_token.type in ('NUMBER', 'STRING', 'ID'):
                        value = self.parse_identifier() if value_token.type == 'ID' else self.consume().value
                        logger.info(f"Parsed parameter: {key} = {value}")
                    else:
                        logger.error(f"Invalid parameter value at line {value_token.line} , column {value_token.column}")
                        raise ValueError(f"Invalid parameter value at line {value_token.line}")
                    params.append((key, value))
                else:
                    logger.info(f"Parsed identifier as parameter: {token.value}")
                    value = self.parse_identifier()
                    params.append(value)
            elif token.type in ('NUMBER', 'STRING'):
                logger.info(f"Parsed literal parameter: {token.value}")
                value = self.consume().value
                params.append(value)
            else:
                logger.error(f"Unexpected token in parameters: {token.type} at line {token.line} , column {token.column}")
                raise ValueError(f"Unexpected token in parameters: {token.type} at line {token.line} , column {token.column}")

            if self.current_token() and self.current_token().type == 'COMMA':
                self.consume('COMMA')
                continue
            else:
                break
        self.consume('RPAREN')
        logger.info("Parsed 'CUE' parameters: %s", params)
        return params

    def parse_wait(self):
        logger.info("Parsing 'WAIT' command")
        self.consume('WAIT')
        number_token = self.consume('NUMBER')
        number = float(number_token.value)
        time_unit = 'ms'  # default unit
        if self.current_token() and self.current_token().type == 'ID':
            time_unit = self.consume('ID').value
        logger.info(f"Parsed 'WAIT' command: {number} {time_unit}")
        return {'duration': number, 'unit': time_unit}

if __name__ == "__main__":
    sample_text = '''
SETTING "setting"
PLAYBACK "playback_lib_250601"

SHOW 1 START
    CUE {
        IN BPM, RATE, LIGHT

        FUNC wave1(x) = sin(x)

        INTERVAL 4

        DIMMER{
            INTERVAL[1-4]{
                LIGHT.L DIMMER func wave1 from 0 to PI
                LIGHT.R DIMMER func wave1 from 0 to PI
            }
        }
    } CUE END

    WAIT 4 beats

    CUE cross_back_01(120, RATE=2, LIGHT=FACE.ALL) CUE END
SHOW END
'''

from lexer import Lexer
lexer = Lexer(sample_text)
tokens = list(lexer.generate_tokens())
logger.info(f"=======================finished lexing, got {len(tokens)} tokens===========================")
parser = ShowParser(tokens)
result = parser.parse()

import pprint
pprint.pprint(result)
logger.info("Parsing completed successfully")
logger.info("Final AST:")
logger.info(pprint.pformat(result))