from cue_parser import CueParser

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
        if not token:
            raise ValueError("Unexpected end of input")
        if expected_type and token.type != expected_type:
            raise ValueError(f"Expected {expected_type} but got {token.type} at line {token.line} , column {token.column} , column {token.column}")
        if expected_value and token.value != expected_value:
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
        self.consume('SETTING')
        token = self.consume('STRING')
        return token.value.strip('"')

    def parse_playback(self):
        self.consume('PLAYBACK')
        token = self.consume('STRING')
        return token.value.strip('"')

    def parse_show_block(self):
        self.consume('SHOW')
        number = int(self.consume('NUMBER').value)
        self.consume('START')
        body = self.parse_show_body()
        self.consume('SHOW')
        self.consume('END')
        return {'number': number, 'body': body}

    def parse_show_body(self):
        commands = []
        while True:
            token = self.current_token()
            if token is None:
                break
            if token.type == 'SHOW' and self.tokens[self.pos + 1].type == 'END':
                break
            if token.type == 'CUE':
                cue_call = self.parse_cue_call()
                commands.append({'type': 'CUE', 'data': cue_call})
            elif token.type == 'WAIT':
                wait_cmd = self.parse_wait()
                commands.append({'type': 'WAIT', 'data': wait_cmd})
            elif token.type == 'COMMENT':
                self.consume('COMMENT')  # skip comment
            else:
                raise ValueError(f"Unexpected token {token.type} at line {token.line} , column {token.column}")
        return commands

    def parse_cue_call(self):
        self.consume('CUE')
        token = self.current_token()
        if token.type == 'LBRACE':
            # inline cue，呼叫 parse_inline_cue
            # 注意要調整 pos，讓 CueParser 從 'CUE' token 開始解析
            # 先退回一格回到 'CUE'，給 CueParser 完整 Token
            self.pos -= 1
            inline_tokens = self.tokens[self.pos:]  # 從此開始的所有 token
            cue_parser = CueParser(inline_tokens)
            cue_ast = cue_parser.parse(inline=True)
            # 解析完後調整 ShowParser pos 到 CueParser 結束位置
            self.pos += cue_parser.pos
            print(cue_ast,"\n\n\n")
            return cue_ast
        else:
            cue_name = self.consume('ID').value
            params = None
            if self.current_token() and self.current_token().type == 'LPAREN':
                params = self.parse_cue_params()
            body = None
            self.consume('CUE')
            self.consume('END')
            return {'name': cue_name, 'params': params, 'body': body}

    def parse_identifier(self):
        # 解析類似 FACE.ALL、LIGHT.L 等帶點的名稱
        token = self.consume('ID')
        name = token.value
        while self.current_token() and self.current_token().type == 'DOT':
            self.consume('DOT')
            next_id = self.consume('ID')
            name += '.' + next_id.value
        return name

    def parse_cue_params(self):
        self.consume('LPAREN')
        params = []
        # 先檢查是否直接是右括號，表示空參數
        if self.current_token() and self.current_token().type == 'RPAREN':
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
                    else:
                        raise ValueError(f"Invalid parameter value at line {value_token.line}")
                    params.append((key, value))
                else:
                    value = self.parse_identifier()
                    params.append(value)
            elif token.type in ('NUMBER', 'STRING'):
                value = self.consume().value
                params.append(value)
            else:
                raise ValueError(f"Unexpected token in parameters: {token.type} at line {token.line} , column {token.column}")

            if self.current_token() and self.current_token().type == 'COMMA':
                self.consume('COMMA')
                continue
            else:
                break
        self.consume('RPAREN')
        return params

    def parse_wait(self):
        self.consume('WAIT')
        number_token = self.consume('NUMBER')
        number = float(number_token.value)
        time_unit = 'ms'  # default unit
        if self.current_token() and self.current_token().type == 'ID':
            time_unit = self.consume('ID').value
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
parser = ShowParser(tokens)
result = parser.parse()

import pprint
pprint.pprint(result)