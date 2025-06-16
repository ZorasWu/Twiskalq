from collections import namedtuple
import sympy as sp
import Pylogger

logger = Pylogger.get_logger()
Pylogger.logger_enable()  # 啟用日誌記錄
logger_showtoken = False  # 是否顯示 Token 日誌
enable_lexer_log = True  # 啟用 Lexer 日誌記錄

if not enable_lexer_log:
    logger.setLevel(Pylogger.Levels['CUE_PARSER'])  # 如果不啟用 Lexer 日誌，則設定為 PARSER 級別
else:
    logger.setLevel(Pylogger.Levels['LEXER'])  # 啟用 Lexer 日誌記錄

# Token 定義
Token = namedtuple('Token', ['type', 'value', 'line', 'column'])

class CueParser:
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
            logger.cons(f"\t\t\t Consume ('NEWLINE','\\n') at pos {self.pos}")
        else:
            logger.cons(f"\t\t\t Consume ('{token.type}','{token.value}') at pos {self.pos}")
        if not token:
            logger.error(f"Unexpected end of input at pos {self.pos}")
            raise ValueError("Unexpected end of input")
        if expected_type and token.type != expected_type:
            logger.error(f"Expected {expected_type} but got {token.type} at line {token.line}, column {token.column}")
            raise ValueError(f"Expected {expected_type} but got {token.type} at line {token.line}")
        if expected_value and token.value != expected_value:
            logger.error(f"Expected {expected_value} but got {token.value} at line {token.line}")
            raise ValueError(f"Expected {expected_value} but got {token.value} at line {token.line}")
        self.pos += 1
        return token

    def parse(self, inline=False):
        logger.info(f"Starting parse with inline={inline}")
        self.consume('CUE')
        if inline:
            # 僅解析區塊，無 cue_name、無 START
            logger.debug("Parsing inline 'CUE' block")
            self.consume('LBRACE')
            body = self.parse_block(inline=True)
            self.consume('RBRACE')
            self.consume('CUE')
            self.consume('END')
            logger.info("End of inline 'CUE' block")
            return {'CUE': {'name': None, 'body': body}}
        else:
            # 正常解析帶名稱與 START 的 Cue
            logger.debug("Parsing full 'CUE' block")
            cue_name = self.consume('ID').value
            logger.info(f"Parsing CUE with name: {cue_name}")
            self.consume('START')
            body = self.parse_block()
            self.consume('CUE')
            self.consume('END')
            logger.info("End of 'CUE' block")
            return {'CUE': {'name': cue_name, 'body': body}}

    def parse_block(self,inline=False):
        result = {}
        while True:
            token = self.current_token()
            if token is None:
                break
            # CUE end 是區塊結束標誌
            if inline and token.type == 'RBRACE':
                logger.debug("Detect 'RBRACE' and end inline CUE block")
                break
            # 如果是 CUE 區塊結束，則跳出迴圈
            if token.type == 'CUE':
                next_token = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
                if next_token and next_token.type == 'END':
                    logger.debug("Detect 'CUE' 'END' and end 'CUE' block")
                    break
            if token.type == 'IN':
                result['IN'] = self.parse_in()
            elif token.type == 'FUNC':
                if 'FUNC' not in result:
                    result['FUNC'] = {}
                result['FUNC'].update(self.parse_func())
            elif token.type == 'INTERVAL':
                result['INTERVAL'] = self.parse_interval()
            elif token.type in ('DIMMER', 'COLOR', 'STROBE', 'OTHERS'):
                result[token.type] = self.parse_command_block(token.type)
            elif token.type == 'NEWLINE':
                logger.debug("Skipping 'NEWLINE' token")
                self.consume('NEWLINE')
            else:
                logger.error(f"Unexpected token {token.type} at line {token.line}")
                raise ValueError(f"Unexpected token {token.type} at line {token.line}")
        return result

    def parse_in(self):
        logger.info("Parsing 'IN' block")
        self.consume('IN')
        params = []
        while True:
            token = self.consume('ID')
            params.append(token.value)
            if self.current_token() and self.current_token().type == 'COMMA':
                self.consume('COMMA')
            else:
                break
        logger.debug(f"IN params: {params}")
        logger.info("End of 'IN' block")
        return params

    def parse_func(self):
        logger.info("Parsing 'FUNC' block")
        self.consume('FUNC')
        func_name = self.consume('ID').value
        logger.debug(f"Function name: {func_name}")
        self.consume('LPAREN')
        arg = self.consume('ID').value
        logger.debug(f"Function argument: {arg}")
        self.consume('RPAREN')
        self.consume('OP', '=')
        expr_tokens = []
        # 收集等號後直到換行或區塊開始的 tokens 為函式表達式
        while True:
            token = self.current_token()
            if token is None or token.type in ('NEWLINE', 'DIMMER', 'COLOR', 'STROBE', 'OTHERS', 'IN', 'INTERVAL', 'CUE', 'FUNC'):
                logger.debug(f"Get token ('{token.type}','{token.value}')end function block")
                break
            expr_tokens.append(token.value)
            self.pos += 1
        expr_str = ''.join(expr_tokens)
        logger.debug(f"Function expression: '{expr_str}'")
        func = self.build_func_with_sympy(arg, expr_str)
        logger.info(f"Function '{func_name}' parsed successfully")
        return {func_name: func}

    def build_func_with_sympy(self, arg, expr_str):
        logger.info(f"Building function with sympy: '{expr_str}'")
        x = sp.symbols(arg)
        allowed_funcs = {
            'sin': sp.sin,
            'cos': sp.cos,
            'pi': sp.pi,
            'tan': sp.tan,
            'exp': sp.exp,
            'sqrt': sp.sqrt,
            'Abs': sp.Abs,
            'log': sp.log,
            'Max': sp.Max,
            'Min': sp.Min,
        }
        try:
            expr = sp.sympify(expr_str, locals=allowed_funcs)
        except sp.SympifyError as e:
            raise ValueError(f"Failed to parse expression '{expr_str}': {e}")
        func = sp.lambdify(x, expr, modules=["math"])
        logger.info(f"Function '{expr_str}' built successfully")
        return func

    def parse_interval(self):
        self.consume('INTERVAL')
        logger.info("Parsing 'INTERVAL' block")
        number = int(self.consume('NUMBER').value)
        logger.debug(f"Interval number: {number}")
        logger.info("End of 'INTERVAL' block")
        return number

    def parse_command_block(self, block_type):
        logger.info(f"Parsing '{block_type}' block")
        self.consume(block_type)
        self.consume('LBRACE')

        block_content = {}

        while True:
            token = self.current_token()
            if token is None:
                logger.error(f"Unexpected end of input inside {block_type} block")
                raise ValueError(f"Unexpected end of input inside {block_type} block")
            if token.type == 'RBRACE':
                self.consume('RBRACE')
                break
            elif token.type == 'NEWLINE':
                self.consume('NEWLINE')  # 跳過換行
                continue
            elif token.type == 'INTERVAL':
                interval_key, cmds = self.parse_interval_block()
                logger.debug(f"Parsed interval block {interval_key} with cmds {cmds}")
                block_content[interval_key] = cmds
            elif block_type == 'OTHERS' and token.type == 'ID':
                cmd = self.parse_command_line()  # 會得到 ('cmd', 'bypass') 這樣的元組
                logger.debug(f"Add OTHERS command: {cmd}")
                # 將狀態字串直接取出，並存在 block_content['OTHERS']，不必用列表
                # 因為 OTHERS 區塊通常只會有一種狀態
                block_content[block_type] = cmd[1]  # 取元組中的字串部分
                break
            else:
                logger.error(f"Unexpected token {token.type} inside {block_type} block at line {token.line}")
                raise ValueError(f"Unexpected token {token.type} inside {block_type} block at line {token.line}")

        logger.info(f"End of '{block_type}' block with content: {block_content}")
        return block_content

    def parse_interval_block(self):
        logger.info("Parsing 'INTERVAL[...]' block")
        self.consume('INTERVAL')
        self.consume('LSQUARE')
        start = self.consume('NUMBER').value
        end = start
        if self.current_token() and self.current_token().type == 'OP' and self.current_token().value == '-':
            self.consume('OP')
            end = self.consume('NUMBER').value
            logger.debug(f"Interval range: {start}-{end}")
        self.consume('RSQUARE')
        self.consume('LBRACE')
        cmds = []
        while True:
            token = self.current_token()
            if token is None:
                logger.error("Unexpected end of input inside interval block")
                raise ValueError("Unexpected end of input inside interval block")
            if token.type == 'RBRACE':
                self.consume('RBRACE')
                break
            parsed_cmd = self.parse_command_line()
            cmds.append(parsed_cmd)
            logger.debug(f"Add command: {parsed_cmd}")
        logger.info(f"End of 'INTERVAL[{start}-{end}]' block with commands: {cmds}")
        return f"INTERVAL[{start}-{end}]", cmds

    def parse_command_line(self):
        logger.info("Parsing command line")
        items = []
        while True:
            token = self.current_token()
            if token is None or token.type in ('NEWLINE', 'RBRACE'):
                # 如果是換行或區塊結束，則結束該指令
                logger.debug(f"End of command line with token: {token}")
                self.consume(token.type) if token else None
                break
            if token.type == 'COMMA':
                self.consume('COMMA')  # 忽略逗號
                continue
            items.append(self.consume().value)
        # 將指令拆成 key-value 或原始字串
        # 這裡簡單回傳該行字串，也可進一步解析
        logger.debug(f"Command line items: {items}")
        return ('cmd', ' '.join(items))


if __name__ == "__main__":
    sample_text = """
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
    """
    from lexer import Lexer
    import pprint
    lexer = Lexer(sample_text)
    tokens = list(lexer.generate_tokens())
    logger.info(f"=======================finished lexing, got {len(tokens)} tokens===========================")
    logger.info(f"\n\tTokens:\n" + '\n'.join('\t' + line for line in pprint.pformat(tokens).splitlines())) if logger_showtoken else None
    parser = CueParser(tokens)
    result = parser.parse(inline=0)

    
    pprint.pprint(result)
    logger.info("Parsing completed successfully")
    logger.info("Parsed CUE structure:")
    logger.info(pprint.pformat(result))


    # 示範呼叫解析後的函式
    if 'FUNC' in result['CUE']['body']:
        funcs = result['CUE']['body']['FUNC']
        for fname, f in funcs.items():
            print(f"{fname}(0) =", f(0))
            print(f"{fname}(pi/2) =", f(3.1415/2))