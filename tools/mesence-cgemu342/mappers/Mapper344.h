#pragma once
#include "pch.h"
#include "NES/Mappers/Nintendo/MMC3.h"

class Mapper344 : public MMC3
{
private:
	uint8_t _reg = 0;
	uint8_t _resetCounter = 0;

protected:
	void InitMapper() override
	{
		_reg = 0;
		_resetCounter = 0;
		MMC3::InitMapper();
		AddRegisterRange(0x6000, 0x7FFF, MemoryOperation::Write);
	}

	void Reset(bool softReset) override
	{
		_reg = 0;
		_resetCounter++;
		MMC3::Reset(softReset);
	}

	void Serialize(Serializer& s) override
	{
		MMC3::Serialize(s);
		SV(_reg); SV(_resetCounter);
	}

	void SelectChrPage(uint16_t slot, uint16_t page, ChrMemoryType memoryType = ChrMemoryType::Default) override
	{
		uint16_t mask = (_reg & 0x04) ? 0xFF : 0x7F;
		uint16_t mapped = (page & mask) | (((uint16_t)_reg << 7) & ~mask);
		MMC3::SelectChrPage(slot, mapped, memoryType);
	}

	void SelectPrgPage(uint16_t slot, uint16_t page, PrgMemoryType memoryType = PrgMemoryType::PrgRom) override
	{
		if(_reg & 0x04) {
			if(slot == 0) {
				uint16_t bank32 = ((uint16_t)_reg << 2) | (page >> 2);
				for(uint16_t i = 0; i < 4; i++) MMC3::SelectPrgPage(i, bank32 * 4 + i, memoryType);
			}
		} else {
			MMC3::SelectPrgPage(slot, ((uint16_t)_reg << 4) | (page & 0x0F), memoryType);
		}
	}

	void WriteRegister(uint16_t addr, uint8_t value) override
	{
		if(addr < 0x8000) {
			auto st = GetState();
			if((st.RegA001 & 0x80) && !(st.RegA001 & 0x40)) {
				_reg = (uint8_t)addr;
				UpdateState();
			}
		} else {
			MMC3::WriteRegister(addr, value);
		}
	}
};
