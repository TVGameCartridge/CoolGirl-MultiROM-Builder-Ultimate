#pragma once
#include "pch.h"
#include "NES/Mappers/JyCompany/JyCompany.h"

// Mapper 358 is a JY-ASIC derivative. MesenCE's JY core supplies the
// register, IRQ, mirroring and base PRG/CHR behavior used by this board.
class Mapper358 : public JyCompany
{
};
