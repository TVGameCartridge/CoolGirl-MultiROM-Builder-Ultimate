#pragma once
void CGEMU342_Init(const char *baseDirectory);
void CGEMU342_OnRomLoaded(const char *name);
void CGEMU342_OnCoolGirlWrite(unsigned int address, unsigned char value);
void CGEMU342_FrameBoundary();
