from collections import namedtuple

Token = namedtuple('Token', ['type', 'value', 'line', 'column'])

class SettingParser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current_token(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self, expected_type=None):
        token = self.current_token()
        if not token:
            raise ValueError("Unexpected end of input")
        if expected_type and token.type != expected_type:
            raise ValueError(f"Expected {expected_type} but got {token.type} at line {token.line}")
        self.pos += 1
        return token

    def parse(self):
        result = {
            "LIBS": [],
            "FIXTURES": [],
            "PATCHES": [],
            "GROUPS": []
        }
        while self.current_token():
            token = self.current_token()
            if token.type == 'LIBS':
                result['LIBS'] = self.parse_libs()
            elif token.type == 'FIXTURE':
                result['FIXTURES'].append(self.parse_fixture())
            elif token.type == 'PATCH':
                result['PATCHES'].extend(self.parse_patch())
            elif token.type == 'GROUP':
                result['GROUPS'].append(self.parse_group())
            else:
                raise ValueError(f"Unexpected token {token.type} at line {token.line}")
        return result

    def parse_libs(self):
        self.consume('LIBS')
        self.consume('LSQUARE')
        libs = []
        while True:
            token = self.consume('STRING')
            libs.append(token.value.strip('"'))
            if self.current_token() and self.current_token().type == 'COMMA':
                self.consume('COMMA')
            else:
                break
        self.consume('RSQUARE')
        return libs

    def parse_fixture(self):
        self.consume('FIXTURE')
        fixture_type = self.consume('ID').value
        number = int(self.consume('NUMBER').value)
        aliases = []
        if self.current_token() and self.current_token().type == 'LSQUARE':
            self.consume('LSQUARE')
            while True:
                token = self.consume('STRING')
                aliases.append(token.value.strip('"'))
                if self.current_token() and self.current_token().type == 'COMMA':
                    self.consume('COMMA')
                else:
                    break
            self.consume('RSQUARE')
        return {
            "fixture_type": fixture_type,
            "number": number,
            "aliases": aliases
        }

    def parse_patch(self):
        self.consume('PATCH')
        self.consume('LBRACE')
        patches = []
        while self.current_token() and self.current_token().type == 'LBRACE':
            self.consume('LBRACE')
            universe_token = self.consume('STRING')
            if universe_token.value.strip('"') != "UNIVERSE":
                raise ValueError(f"Expected 'UNIVERSE' key at line {universe_token.line}")
            self.consume('COLON')
            universe_name = self.consume('STRING').value.strip('"')
            self.consume('COMMA')

            patches_token = self.consume('STRING')
            if patches_token.value.strip('"') != "PATCHES":
                raise ValueError(f"Expected 'PATCHES' key at line {patches_token.line}")
            self.consume('COLON')
            self.consume('LBRACE')
            patch_dict = {}
            while self.current_token() and self.current_token().type == 'STRING':
                alias = self.consume('STRING').value.strip('"')
                self.consume('COLON')
                addr = int(self.consume('NUMBER').value)
                if self.current_token() and self.current_token().type == 'COMMA':
                    self.consume('COMMA')
                patch_dict[alias] = addr
            self.consume('RBRACE')
            self.consume('RBRACE')
            patches.append({"UNIVERSE": universe_name, "PATCHES": patch_dict})
            # 可能有多組，逗號可選擇性忽略
            if self.current_token() and self.current_token().type == 'COMMA':
                self.consume('COMMA')
        self.consume('RBRACE')
        return patches

    def parse_group(self):
        self.consume('GROUP')
        group_types = []
        # 判斷是否有 < ... > 群組類型
        if self.current_token() and self.current_token().type == 'LT':
            self.consume('LT')  # 吃掉 '<'
            while True:
                token = self.consume('ID')
                group_types.append(token.value)
                if self.current_token() and self.current_token().type == 'COMMA':
                    self.consume('COMMA')
                    continue
                else:
                    break
            self.consume('GT')  # 吃掉 '>'

        group_name = self.consume('ID').value

        aliases = []
        if self.current_token() and self.current_token().type == 'LSQUARE':
            self.consume('LSQUARE')
            while True:
                token = self.consume('STRING')
                aliases.append(token.value.strip('"'))
                if self.current_token() and self.current_token().type == 'COMMA':
                    self.consume('COMMA')
                else:
                    break
            self.consume('RSQUARE')

        return {
            "group_types": group_types,
            "group_name": group_name,
            "aliases": aliases
        }


if __name__ == "__main__":
    # 這裡用 Lexer 產生 token，測試 SettingParser
    from lexer import Lexer  # 確保 lexer.py 在同目錄下且已實作

    sample_text = '''
LIBS [
    "color_lib_250601",
    "fixture_lib_250601",
    "func_lib",
    "playback_lib_250601"
]

FIXTURE PAR_4W54 8 ["A","B","C","D","E","F","G","H"] 
FIXTURE FOG_XL 2 ["FOG_L","FOG_R"]

PATCH {
    {
        "UNIVERSE": "A",
        "PATCHES": {
            "A": 1,
            "B": 9,
            "C": 17,
            "D": 25,
            "E": 33,
            "F": 41,
            "G": 48,
            "H": 57,
        }
    },
    {
        "UNIVERSE": "B",
        "PATCHES": {
            "FOG_L": 250,
            "FOG_R": 251
        }
    }
}
GROUP FOG ["FOG_L","FOG_R"]
GROUP <LR> FACE ["A","B"]
GROUP <OE,LR> BACK ["C","D","E","F","G","H"]
    '''

    lexer = Lexer(sample_text)
    tokens = list(lexer.generate_tokens())
    parser = SettingParser(tokens)
    result = parser.parse()

    import pprint
    pprint.pprint(result)