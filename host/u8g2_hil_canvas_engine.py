import serial
import struct
import time

# ==============================================================================
# HARDWARE COMMUNICATION ENGINE
# ==============================================================================
# To add a new command, create an opcode entry for it here
OP_BOX      = 0x01
OP_CIRCLE   = 0x02  
OP_CLEAR    = 0x03
OP_TEXT     = 0x04  
OP_FONT     = 0x05
OP_FRAME    = 0x06  
OP_LINE     = 0x07  
OP_DISC     = 0x08  
OP_RBOX     = 0x09
OP_RFRAME   = 0x0A
OP_PIXEL    = 0x0B  
OP_ROTATE   = 0x0C 
OP_RENDER   = 0x0D  
OP_ICON     = 0x0E  
OP_MODE     = 0x0F  
OP_CONTRAST = 0x10
OP_SLEEP    = 0x11  
OP_WAKE     = 0x12  

class HardwareBridge:
    def __init__(self, port='COM1', baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(1.5) 
            return True
        except serial.SerialException as e:
            print(f"[ERROR] Connection failed on {self.port}: {e}")
            return False

    def send_packet(self, opcode, x=0, y=0, p1=0, p2=0, p3=0, text="", auto_render=1):
        if not self.ser or not self.ser.is_open:
            return False
        
        encoded_text = text[:55].encode('ascii')
        padding = 0

        # PACKET STRUCTURE
        packet = struct.pack('8B 56s', opcode, x, y, p1, p2, p3, auto_render, padding, encoded_text)
        
        try:
            self.ser.write(packet)
            self.ser.flush()

            ack = self.ser.read(1)
            if not ack:
                print("[WARNING] Hardware Timeout. Controller did not acknowledge.")
                return False
            
            return True
        
        except Exception as e:
            print(f"[ERROR] Write failure: {e}")
            return False

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

# ==============================================================================
# COMMAND HISTORY MANAGER & C-MACRO EXPORT
# ==============================================================================
class CommandHistoryManager:
    def __init__(self):
        self.history = []  

    def add(self, c_string, packet_args):
        self.history.append({"c_code": c_string, "packet": packet_args})

    def clear_all(self, bridge):
        bridge.send_packet(OP_CLEAR)
        self.history.clear()
        print("Screen cleared.")

    def undo_last(self, bridge):
        if not self.history:
            print("History empty.")
            return

        popped = self.history.pop()
        print(f"Undone: {popped['c_code']}")

        bridge.send_packet(OP_CLEAR)
        
        # Send shapes to the microcontroller RAM without updating the glass
        for cmd in self.history:
            bridge.send_packet(*cmd["packet"], auto_render=0)
            
        # Trigger final push to update the physical screen
        bridge.send_packet(OP_RENDER, auto_render=1)

    def export_macro(self):
        if not self.history:
            print("No active graphics history to export")
            return
        
        # Print C code
        print("/* =================== main.c ================== */")
        print("u8g2_ClearBuffer(&u8g2);")
        for idx, cmd in enumerate(self.history):
            print(f"{cmd['c_code']}")
        print("u8g2_SendBuffer(&u8g2);")
        print("/* ============================================= */")

# ==============================================================================
# COMMAND PARSER & DICTIONARY
# ==============================================================================
def print_help_menu():
    print("""
================================ GRAPHICS ENGINE COMMANDS ================================
  [Filled Shapes]
  box <x> <y> <w> <h>      : Renders a solid box (Top left coordinates)
  disc <x> <y> <r>         : Renders a solid circle (Center coordinates)
  rbox <x> <y> <w> <h> <r> : Renders a solid rounded box (Top left coordinates)

  [Outlines & Lines]
  frame <x> <y> <w> <h>    : Renders a hollow box outline (Top left coordinates)
  circle <x> <y> <r>       : Renders a hollow circle outline (Center coordinates)
  rframe <x> <y> <w> <h> <r> : Renders a hollow rounded box outline (Top left coordinates)
  line <x1> <y1> <x2> <y2> : Draws a line between two points
  pixel <x> <y>            : Draws a single dot

  [Typography]
  text <x> <y> <string>    : Renders dynamic text (e.g., text 10 20 Hello World)
  (Coordinates generally not top left, dependent on rotation and u8g2 settings)
  
  setfont <name>           : Options: tiny, small, standard, bold, title, clock
  rotate <degrees>         : Rotates text. Options: 0, 90, 180, 270

  [Hardware & Styling]
  icon <x> <y> <name>      : Draws internal XBM (e.g., icon 10 5 wifi)
  mode <0/1/2>             : 0=Eraser, 1=Normal, 2=XOR Highlight
  (XOR may be buggy, switching between eraser and normal may yield better results)
  
  contrast <0-255>         : Sets physical screen contrast
  sleep                    : Turns off the display panel
  wake                     : Turns on the display panel

  [System]
  clear                    : Wipes the current screen
  undo                     : Reverts the last drawn command
  next                     : Exports your layout script to native C-code
  exit                     : Closes the bridge
==========================================================================================
""")

def parse_and_execute(user_input, bridge, history):
    tokens = user_input.strip().split()
    if not tokens:
        return

    base_cmd = tokens[0].lower()

    try:
        # --- MENU ---
        if base_cmd == "help":
            print_help_menu()
            return

        elif base_cmd == "clear":
            history.clear_all(bridge)
            return

        elif base_cmd == "undo":
            history.undo_last(bridge)
            return

        elif base_cmd == "next":
            history.export_macro()
            return

        # --- SHAPES ---
        elif base_cmd == "box":
            x, y, w, h = map(int, tokens[1:5])
            c_text = f"u8g2_DrawBox(&u8g2, {x}, {y}, {w}, {h});"
            packet_args = (OP_BOX, x, y, w, h, 0, "")

        elif base_cmd == "frame":
            x, y, w, h = map(int, tokens[1:5])
            c_text = f"u8g2_DrawFrame(&u8g2, {x}, {y}, {w}, {h});"
            packet_args = (OP_FRAME, x, y, w, h, 0, "")

        elif base_cmd == "circle":
            x, y, r = map(int, tokens[1:4])
            c_text = f"u8g2_DrawCircle(&u8g2, {x}, {y}, {r}, U8G2_DRAW_ALL);"
            packet_args = (OP_CIRCLE, x, y, r, 0, 0, "")

        elif base_cmd == "disc":
            x, y, r = map(int, tokens[1:4])
            c_text = f"u8g2_DrawDisc(&u8g2, {x}, {y}, {r}, U8G2_DRAW_ALL);"
            packet_args = (OP_DISC, x, y, r, 0, 0, "")

        elif base_cmd == "line":
            x1, y1, x2, y2 = map(int, tokens[1:5])
            c_text = f"u8g2_DrawLine(&u8g2, {x1}, {y1}, {x2}, {y2});"
            packet_args = (OP_LINE, x1, y1, x2, y2, 0, "")

        elif base_cmd == "pixel":
            x, y = map(int, tokens[1:3])
            c_text = f"u8g2_DrawPixel(&u8g2, {x}, {y});"
            packet_args = (OP_PIXEL, x, y, 0, 0, 0, "")

        elif base_cmd == "rbox":
            x, y, w, h, r = map(int, tokens[1:6])
            c_text = f"u8g2_DrawRBox(&u8g2, {x}, {y}, {w}, {h}, {r});"
            packet_args = (OP_RBOX, x, y, w, h, r, "")

        elif base_cmd == "rframe":
            x, y, w, h, r = map(int, tokens[1:6])
            c_text = f"u8g2_DrawRFrame(&u8g2, {x}, {y}, {w}, {h}, {r});"
            packet_args = (OP_RFRAME, x, y, w, h, r, "")

        # --- FONTS & TEXT ---
        elif base_cmd == "setfont":
            font_name = tokens[1].lower() 

            # Add an entry here to enable another font
            font_c_map = {
                "tiny": "u8g2_font_4x6_tr",
                "small": "u8g2_font_5x8_tr",
                "standard": "u8g2_font_6x10_tr",
                "bold": "u8g2_font_ncenB08_tr",
                "title": "u8g2_font_helvB12_tr",
                "clock": "u8g2_font_logisoso24_tn"
            }

            if font_name not in font_c_map:
                print("[ERROR] Font must be one of the options specified.")
                return
            
            c_font_name = font_c_map[font_name]
            c_text = f"u8g2_SetFont(&u8g2, {c_font_name});"
            packet_args = (OP_FONT, 0, 0, 0, 0, 0, font_name)

        elif base_cmd == "rotate":
            deg = int(tokens[1])
            dir_map = {0: 0, 90: 1, 180: 2, 270: 3}
            
            if deg not in dir_map:
                print("[ERROR] Degrees must be exactly 0, 90, 180, or 270.")
                return
                
            u8g2_dir = dir_map[deg]
            c_text = f"u8g2_SetFontDirection(&u8g2, {u8g2_dir});"
            packet_args = (OP_ROTATE, 0, 0, u8g2_dir, 0, 0, "")

        elif base_cmd == "text":
            x = int(tokens[1])
            y = int(tokens[2])
            text_str = " ".join(tokens[3:]) 
            c_text = f"u8g2_DrawStr(&u8g2, {x}, {y}, \"{text_str}\");"
            packet_args = (OP_TEXT, x, y, 0, 0, 0, text_str)

        # --- HARDWARE & STYLING ---
        elif base_cmd == "mode":
            val = int(tokens[1])
            
            if val not in [0, 1, 2]:
                print("[ERROR] Mode must be 0 (Eraser), 1 (Normal), or 2 (XOR).")
                return
            
            c_text = f"u8g2_SetDrawColor(&u8g2, {val});"
            packet_args = (OP_MODE, 0, 0, val, 0, 0, "")
            
        elif base_cmd == "contrast":
            val = int(tokens[1]) 
            c_text = f"u8g2_SetContrast(&u8g2, {val});"
            packet_args = (OP_CONTRAST, 0, 0, val, 0, 0, "")
            
        elif base_cmd == "sleep":
            c_text = "u8g2_SetPowerSave(&u8g2, 1);"
            packet_args = (OP_SLEEP, 0, 0, 0, 0, 0, "")
            
        elif base_cmd == "wake":
            c_text = "u8g2_SetPowerSave(&u8g2, 0);"
            packet_args = (OP_WAKE, 0, 0, 0, 0, 0, "")
            
        elif base_cmd == "icon":
            x = int(tokens[1])
            y = int(tokens[2])
            icon_name = tokens[3].lower()
            c_text = f"DrawIcon({x}, {y}, \"{icon_name}\");"
            packet_args = (OP_ICON, x, y, 0, 0, 0, icon_name)

        else:
            print(f"Unknown command: '{base_cmd}'. Type 'help' to get list of available commands.")
            return

        # Send over wire and log to history
        bridge.send_packet(*packet_args)
        history.add(c_text, packet_args)

    except (ValueError, IndexError):
        print(f"[SYNTAX ERROR] Incorrect arguments for command '{base_cmd}'.")
