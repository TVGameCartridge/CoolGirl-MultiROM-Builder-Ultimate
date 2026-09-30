#pragma once
#include <string>

void CGEMU342_Init(const char *baseDirectory);
void CGEMU342_OnRomLoaded(const char *name);
void CGEMU342_Poll();
bool CGEMU342_TakePendingLoad(std::string &path);
