import sys
import argparse
from u8g2_hil_canvas_engine import HardwareBridge, CommandHistoryManager, parse_and_execute

def main():
    parser = argparse.ArgumentParser(description="u8g2 HIL Canvas Console")
    parser.add_argument('--port', type=str, default='COM10', help='Serial port (e.g., COM10 or /dev/ttyUSB0)')
    parser.add_argument('--baudrate', type=int, default=115200, help='Baudrate')
    args = parser.parse_args()

    print(" --------------------=== Console ===----------------------- ")

    bridge = HardwareBridge(port=args.port, baudrate=args.baudrate) 
    history = CommandHistoryManager()

    if not bridge.connect():
        sys.exit(1)

    print("Connection established. Type 'help' to get list of commands.")
    
    try:
        while True:
            user_input = input(" >> ")
            if user_input.strip().lower() == "exit":
                break
            parse_and_execute(user_input, bridge, history)
            
    except KeyboardInterrupt:
        pass
    finally:
        bridge.close()
        print("^C")

if __name__ == "__main__":
    main()
