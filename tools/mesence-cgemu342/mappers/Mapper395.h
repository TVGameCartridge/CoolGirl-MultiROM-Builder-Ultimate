#pragma once
#include "pch.h"
#include "NES/Mappers/Nintendo/MMC3.h"

class Mapper395 : public MMC3
{
private:
	uint8_t _ex[2] = {};
protected:
	void InitMapper() override
	{
		_ex[0] = _ex[1] = 0;
		MMC3::InitMapper();
		AddRegisterRange(0x6000, 0x7FFF, MemoryOperation::Write);
	}
	void Reset(bool softReset) override
	{
		_ex[0] = _ex[1] = 0;
		MMC3::Reset(softReset);
	}
	void Serialize(Serializer& s) override
	{
		MMC3::Serialize(s); SVArray(_ex, 2);
	}
	void SelectChrPage(uint16_t slot, uint16_t page, ChrMemoryType memoryType = ChrMemoryType::Default) override
	{
		uint16_t mask = (_ex[1] & 0x40) ? 0x7F : 0xFF;
		uint16_t mapped = (page & mask) | ((_ex[1] & 0x10) << 3) | ((_ex[0] & 0x30) << 4) | ((_ex[1] & 0x20) << 5);
		MMC3::SelectChrPage(slot, mapped, memoryType);
	}
	void SelectPrgPage(uint16_t slot, uint16_t page, PrgMemoryType memoryType = PrgMemoryType::PrgRom) override
	{
		uint16_t mask = (_ex[1] & 0x08) ? 0x0F : 0x1F;
		uint16_t mapped = (page & mask) | ((_ex[0] & 0x30) << 1) | ((_ex[0] & 0x08) << 4) | ((_ex[1] & 0x01) << 4);
		MMC3::SelectPrgPage(slot, mapped, memoryType);
	}
	void WriteRegister(uint16_t addr, uint8_t value) override
	{
		if(addr < 0x8000) {
			if(!(_ex[1] & 0x80)) {
				_ex[(addr >> 4) & 1] = value;
				UpdateState();
			}
		} else MMC3::WriteRegister(addr, value);
	}
};
