#ifndef U8G2_HIL_H
#define U8G2_HIL_H

#include "main.h"
#include "u8g2.h"
#include <string.h>

void SetActiveFont(u8g2_t* u8g2_inst, const char* font_name);
void DrawIcon(u8g2_t* ug82_inst, uint8_t x, uint8_t y, const char* icon_name);
void ProcessUARTPacket(uint8_t* rx_buffer, u8g2_t* u8g2_inst, UART_HandleTypeDef* huart);

#endif