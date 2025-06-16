import re
import math
import sympy as sp

class CueParser:
    def __init__(self, dsl_text):
        self.text = dsl_text
        self.pos = 0
        self.length = len(dsl_text)
        self.lines = [line.strip() for line in dsl_text.splitlines() if line.strip() and not line.strip().startswith("#")]
        self.index = 0
        self.result = {}

    def parse(self):
        # 預期從 CUE 開始，結束於 CUE end
        if not self.lines[self.index].startswith("CUE"):
            raise ValueError("DSL must start with 'CUE'")
        cue_line = self.lines[self.index]
        cue_name = cue_line.split()[1]
        self.index += 1
        self.result['CUE'] = {'name': cue_name, 'body': {}}

        # 解析 CUE 內容直到遇到 "CUE end"
        while self.index < len(self.lines):
            line = self.lines[self.index]
            if line == "CUE end":
                break
            key, value = self.parse_line(line)
            if key:
                self.result['CUE']['body'][key] = value
            self.index += 1

        return self.result

    def parse_line(self, line):
        # 處理 IN 參數輸入
        if line.startswith("IN "):
            params = line[3:].split(",")
            params = [p.strip() for p in params]
            return "IN", params

        # 處理 FUNC 函式定義
        if line.startswith("FUNC "):
            # 例如 FUNC wave2(x) = 1-sin(x)
            m = re.match(r"FUNC\s+(\w+)\((\w+)\)\s*=\s*(.+)", line)
            if m:
                fname, arg, expr = m.groups()
                # 將 expr 轉成可用函式 (lambda)
                func = CueParser.build_func_with_sympy(arg, expr)
                return "FUNC", {fname: func}
            else:
                raise ValueError(f"Invalid FUNC syntax: {line}")

        # 處理 INTERVAL 數量設定 (INTERVAL 4)
        if line.startswith("INTERVAL "):
            m = re.match(r"INTERVAL\s+(\d+)", line)
            if m:
                count = int(m.group(1))
                return "INTERVAL", count

        # 處理區塊型指令 (DIMMER{...}、COLOR{...}、STROBE{...}、OTHERS{...})
        if re.match(r"^(DIMMER|COLOR|STROBE|OTHERS)\{", line):
            key = line.split("{")[0]
            block_content = self.parse_block()
            return key, block_content

        # 其他行，暫時不處理直接回傳None
        return None, None
    
    def parse_block(self):
        # 解析 { ... } 內內容，支援巢狀
        block_lines = []
        brace_count = 0
        # 目前行含有 {，計數加一
        line = self.lines[self.index]
        brace_count += line.count("{")
        brace_count -= line.count("}")
        # 將該行除去外層大括號內容，留下內部，若有
        content = line[line.find("{")+1:].strip()
        if content:
            block_lines.append(content)
        self.index += 1

        while self.index < len(self.lines) and brace_count > 0:
            line = self.lines[self.index]
            brace_count += line.count("{")
            brace_count -= line.count("}")
            # 除去行尾 } ，只保留內部
            clean_line = line.replace("}", "").strip()
            if clean_line:
                block_lines.append(clean_line)
            self.index += 1

        # 解析 block_lines 內容，可能包含 INTERVAL[...] {...} 或指令
        block_dict = {}
        i = 0
        while i < len(block_lines):
            line = block_lines[i]
            # INTERVAL 範圍判斷
            m = re.match(r"INTERVAL\[(\d+-?\d*)\]\{", line)
            if m:
                interval_range = m.group(1)
                # 找到該區塊結尾 }
                sub_block_lines = []
                brace = 1
                i += 1
                while i < len(block_lines) and brace > 0:
                    l = block_lines[i]
                    brace += l.count("{")
                    brace -= l.count("}")
                    if brace > 0:
                        sub_block_lines.append(l)
                    i += 1
                # 解析子區塊內容（簡化只存文字）
                block_dict[f"INTERVAL[{interval_range}]"] = sub_block_lines
            else:
                # 非INTERVAL區塊，直接存
                block_dict[line] = None
                i += 1
        return block_dict
    
    @staticmethod
    def build_func_with_sympy(arg, expr_str):
        # 建立符號變數
        x = sp.symbols(arg)
        # 將輸入字串轉為sympy表達式，並指定允許的函式名稱
        # 這裡示範允許 sin、cos、pi 等
        allowed_funcs = {
            'sin': sp.sin,
            'cos': sp.cos,
            'pi': sp.pi,
            # 可依需求繼續擴充
        }
        try:
            expr = sp.sympify(expr_str, locals=allowed_funcs)
        except sp.SympifyError as e:
            raise ValueError(f"Failed to parse expression '{expr_str}': {e}")

        # 將符號表達式轉成可計算函式
        func = sp.lambdify(x, expr, modules=["math"])
        return func

if __name__ == "__main__":
    dsl_text = """
    CUE cross_back_01 start
        IN BPM, RATE, LIGHT

        FUNC wave2(x) = 1-sin(x)

        INTERVAL 4

        DIMMER{
            INTERVAL[1-4]{
                LIGHT.L DIMMER func wave1 from 0 to PI
                LIGHT.R DIMMER func wave2 from 0 to PI
            }
        }

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

        STROBE{
            INTERVAL[1-2]{
                LIGHT.ALL STROBE value 0
            }
            INTERVAL[3-4]{
                LIGHT.R STROBE value 255
            }
        }

        OTHERS{bypass}
    CUE end
    """

    parser = CueParser(dsl_text)
    result = parser.parse()

    # 示範呼叫解析後的函式
    print("Parsed result:")
    for k,v in result.items():
        print(f"{k}: {v}")

    # 呼叫 wave2 函式示範
    if 'FUNC' in result['CUE']['body']:
        funcs = result['CUE']['body']['FUNC']
        if 'wave2' in funcs:
            print("wave2(0) =", funcs['wave2'](0))
            print("wave2(pi/2) =", funcs['wave2'](math.pi/2))