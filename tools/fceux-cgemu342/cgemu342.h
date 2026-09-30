#pragma once
void CGEMU342_Init(const char *baseDirectory);
bool CGEMU342_IsContainer(const char *path);
const char *CGEMU342_BaseDirectory();
const char *CGEMU342_EmbeddedLuaChunkName();
const char *CGEMU342_EmbeddedLuaSource();
