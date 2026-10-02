#pragma once
#include "pch.h"
#include "NES/Mappers/Nintendo/MMC3.h"

class Mapper393 : public MMC3
{
private:
	uint8_t _ex0 = 0;
	uint8_t _ex1 = 0;

	uint16_t GetPrgBank(uint8_t bank)
	{
		if((~bank & 1) && _prgMode) bank ^= 2;
		return (bank & 2) ? (0xFE | (bank & 1)) : _registers[6 | (bank & 1)];
	}

protected:
	uint32_t GetChrRamSize() override { return 0x2000; }

	void InitMapper() override
	{
		_ex0 = _ex1 = 0;
		MMC3::InitMapper();
		AddRegisterRange(0x6000, 0x7FFF, MemoryOperation::Write);
	}

	void Reset(bool softReset) override
	{
		_ex0 = _ex1 = 0;
		MMC3::Reset(softReset);
	}

	void Serialize(Serializer& s) override
	{
		MMC3::Serialize(s);
		SV(_ex0); SV(_ex1);
	}

	void UpdatePrgMapping() override
	{
		switch((_ex0 >> 4) & 3) {
			case 0:
			case 1:
				MMC3::UpdatePrgMapping();
				break;
			case 2: {
				uint16_t bank32 = ((GetPrgBank(0) >> 2) & 3) | ((uint16_t)_ex0 << 2);
				for(uint16_t i = 0; i < 4; i++) MMC3::SelectPrgPage(i, bank32 * 4 + i);
				break;
			}
			case 3: {
				uint16_t lo = ((uint16_t)_ex0 << 3) | (_ex1 & 7);
				uint16_t hi = ((uint16_t)_ex0 << 3) | 7;
				MMC3::SelectPrgPage(0, lo * 2); MMC3::SelectPrgPage(1, lo * 2 + 1);
				MMC3::SelectPrgPage(2, hi * 2); MMC3::SelectPrgPage(3, hi * 2 + 1);
				break;
			}
		}
	}

	void UpdateChrMapping() override
	{
		if(_ex0 & 0x08) {
			for(uint16_t i = 0; i < 8; i++) MMC3::SelectChrPage(i, i, ChrMemoryType::ChrRam);
		} else {
			MMC3::UpdateChrMapping();
		}
	}

	void SelectPrgPage(uint16_t slot, uint16_t page, PrgMemoryType memoryType = PrgMemoryType::PrgRom) override
	{
		MMC3::SelectPrgPage(slot, (page & 0x0F) | ((uint16_t)_ex0 << 4), memoryType);
	}

	void SelectChrPage(uint16_t slot, uint16_t page, ChrMemoryType memoryType = ChrMemoryType::Default) override
	{
		MMC3::SelectChrPage(slot, (page & 0xFF) | ((uint16_t)_ex0 << 8), memoryType);
	}

	void WriteRegister(uint16_t addr, uint8_t value) override
	{
		if(addr < 0x8000) {
			_ex0 = (uint8_t)addr;
			UpdateState();
		} else {
			_ex1 = value;
			MMC3::WriteRegister(addr, value);
			UpdateState();
		}
	}
};
