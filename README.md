# U8g2 Hardware-in-the-Loop (HIL) Canvas

A Hardware-in-the-Loop (HIL) testing utility designed for quicker, display-agnostic UI prototyping.

This engine allows a host machine to send real-time graphics commands over a serial connection to any microcontroller running the `u8g2` graphics library. By abstracting the physical display panel, it enables developers to dynamically design, test, and automatically export C-code macros for embedded display layouts.

## Project Structure

The project is decoupled into two primary domains:

1. **Host Engine (`host/`)**: A Python-based CLI that encodes drawing primitives (boxes, circles, dynamic text, XOR modes) into a standardized UART packet. It features a `CommandHistoryManager` that tracks the screen state and can export the live session into native `u8g2` C-code.
2. **Firmware Parser (`firmware/`)**: A lightweight C-based UART parser that decodes incoming packets and maps them directly to native `u8g2` function calls on the microcontroller.

## The UART Packet Protocol

Communication is driven by a strict 64-byte payload transmitted from the host to the MCU. The packet structure is defined via Python's `struct.pack` as follows:

* **Opcode (1 byte)**: Dictates the drawing command (e.g., `0x01` for Box, `0x04` for Text).
* **Coordinates (2 bytes)**: `x` and `y` position parameters.
* **Parameters (3 bytes)**: Up to three shape-specific variables (`w`, `h`, `r`).
* **Auto-Render (1 byte)**: A boolean flag (`0` or `1`) dictating if the MCU should immediately push the RAM buffer to the physical display.
* **Padding (1 byte)**: Reserved for any additional needs.
* **Payload (56 bytes)**: An ASCII-encoded string used for passing text rendering data or calling custom icon names.

The host will block execution until the MCU transmits a single `0xFF` acknowledgment byte, ensuring the serial pipeline remains synchronized.

## Extending the Engine (Adding Custom Commands)

The engine is designed to be easily extensible. To add a new command (e.g., a triangle):

1. **Update the Python Host**: In `u8g2_hil_canvas_engine.py`, add a new opcode constant (e.g., `OP_TRIANGLE = 0x13`). Map your new console command in the `parse_and_execute` function to format the parameters and generate the equivalent `u8g2` C-string for the history manager.
2. **Update the C Parser**: In `u8g2_hil_canvas.c`, add a new case to the switch statement inside `ProcessUARTPacket()` (e.g., `case 0x13: // TRIANGLE`). Map the incoming `x`, `y`, `param1`, etc., to your `u8g2_DrawTriangle` function.

## Porting to Other Microcontrollers

The parser logic (`u8g2_hil_canvas.c`) is entirely independent of the hardware. The repository includes an STM32 reference implementation (targeting an ST7567 SPI display), but the tool can be ported to an ESP32, RP2040, AVR, or any other MCU by replicating these four integration points in your main loop:

1. **Display Setup**: Initialize your specific screen panel using standard `u8g2` hardware setup functions.
2. **UART Pipeline**: Configure your MCU to capture incoming UART packets non-blocking (e.g., using DMA) and note the baudrate. The parser expects a 64-byte receive buffer (`rx_buffer`).
3. **Execute Parser**: Feed the populated receive buffer into `ProcessUARTPacket(rx_buffer, &u8g2, &huart)`.
4. **Hardware Acknowledge**: Ensure your custom parser loop transmits a `0xFF` byte back to the host via UART after the `u8g2_SendBuffer` call executes.

## Usage (Host)

Connect your MCU to your host machine and run the Python bridge:

```bash
cd host
pip install pyserial
python u8g2_hil_canvas.py --port /dev/ttyUSB0 --baudrate 115200
```

Type `help` in the console to see the list of available drawing commands. Execute `next` at any time to output your layout as native C-code.
