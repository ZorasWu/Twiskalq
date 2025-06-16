class Light:
    def __init__(self, name, dmx_base_channel, channel_count=3):
        self.name = name
        self.dmx_base_channel = dmx_base_channel
        self.channel_count = channel_count
        self.dimmer = 0
        self.color = (0,0,0)  # RGB tuple
        self.strobe = 0

    def to_dmx_values(self):
        # 將燈具狀態映射成DMX通道值陣列（此處假設通道1: dimmer, 2-4: RGB）
        dmx_vals = [int(self.dimmer * 255)]
        dmx_vals += list(self.color)
        dmx_vals.append(self.strobe)
        return dmx_vals[:self.channel_count]  # 回傳所需通道數量

class DMXController:
    def __init__(self, lights):
        self.lights = lights
        self.dmx_frame = [0]*512

    def update_frame(self):
        for light in self.lights:
            vals = light.to_dmx_values()
            start = light.dmx_base_channel -1
            for i, val in enumerate(vals):
                self.dmx_frame[start+i] = val

    def send_frame(self):
        # 此處呼叫實際的DMX送出函式
        # 例如使用 OLA 或 pyenttec
        print("Sending DMX frame:", self.dmx_frame[:20])

# 假設解析器回來的結果
cue_result = {
    # 這裡是解析後的資料結構
    # 你會根據INTERVAL及命令更新燈具狀態
    """CUE: {'name': 'cross_back_01', 'body': {'IN': ['BPM', 'RATE', 'LIGHT'], 'FUNC': {'wave2': <function _lambdifygenerated at 0x000001AECAED67A0>}, 'INTERVAL': 4, 'DIMMER': {'INTERVAL[1-4]': ['LIGHT.L DIMMER func wave1 from 0 to PI', 'LIGHT.R DIMMER func wave2 from 0 to PI']}, 'STROBE': {'INTERVAL[1-2]': ['LIGHT.ALL STROBE value 0', 'INTERVAL[3-4]{', 'LIGHT.R STROBE value 255']}}}"""
}

# 呼叫解析後指令，譬如設定某Interval燈光參數
lights = [Light("L1", 1), Light("L2", 4), Light("R1", 10), Light("R2", 13)]
dmx = DMXController(lights)

# 示意：設定L1亮度為0.5，顏色為紅色
lights[0].dimmer = 0.5
lights[0].color = (255,0,0)
dmx.update_frame()
dmx.send_frame()