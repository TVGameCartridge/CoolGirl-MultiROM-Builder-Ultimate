#pragma once
#include "pch.h"
#include "NES/Mappers/Nintendo/MMC3.h"

class Mapper315 : public MMC3
{
private:
	uint8_t _reg = 0;

protected:
	void InitMapper() override
	{
		_reg = 0;
		MMC3::InitMapper();
		AddRegisterRange(0x6800, 0x68FF, MemoryOperation::Write);
	}

	void Reset(bool softReset) override
	{
		_reg = 0;
		MMC3::Reset(softReset);
	}

	void Serialize(Serializer& s) override
	{
		MMC3::Serialize(s);
		SV(_reg);
	}

	void SelectChrPage(uint16_t slot, uint16_t page, ChrMemoryType memoryType = ChrMemoryType::Default) override
	{
		uint16_t mapped = (page & 0xFF) | ((_reg & 0x01) << 8) | ((_reg & 0x02) << 6) | ((_reg & 0x08) << 3);
		MMC3::SelectChrPage(slot, mapped, memoryType);
	}

	void SelectPrgPage(uint16_t slot, uint16_t page, PrgMemoryType memoryType = PrgMemoryType::PrgRom) override
	{
		uint16_t mapped = (page & 0x0F) | ((_reg & 0x06) << 3);
		if(_reg & 0x08) {
			if(slot == 0) {
				MMC3::SelectPrgPage(0, mapped, memoryType);
				MMC3::SelectPrgPage(2, (page & 0x0F) | 0x32, memoryType);
			} else if(slot == 1) {
				MMC3::SelectPrgPage(1, mapped, memoryType);
				MMC3::SelectPrgPage(3, (page & 0x0F) | 0x32, memoryType);
			}
		} else {
			MMC3::SelectPrgPage(slot, mapped, memoryType);
		}
	}

	void WriteRegister(uint16_t addr, uint8_t value) override
	{
		if(addr >= 0x6800 && addr <= 0x68FF) {
			_reg = (uint8_t)addr;
			UpdateState();
		} else {
			MMC3::WriteRegister(addr, value);
		}
	}
};
