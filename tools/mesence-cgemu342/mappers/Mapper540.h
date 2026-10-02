#pragma once
#include "pch.h"
#include "NES/BaseMapper.h"
#include "NES/NesConsole.h"
#include "NES/NesCpu.h"

class Mapper540 : public BaseMapper
{
private:
	uint8_t _prg[4] = {};
	uint8_t _chr[8] = {};
	uint8_t _ex[4] = {};
	bool _irqReload = false;
	bool _irqEnabled = false;
	bool _irqPpuA12 = false;
	bool _irqAutoEnable = false;
	uint8_t _irqLatch = 0;
	uint8_t _irqCount = 0;
	int32_t _irqCount16 = 0;
	uint16_t _lastPpuAddr = 0;

	void ClearIrq() { _console->GetCpu()->ClearIrqSource(IRQSource::External); }
	void RaiseIrq() { _console->GetCpu()->SetIrqSource(IRQSource::External); }

	void Sync()
	{
		uint8_t mask;
		switch(_ex[1] & 3) {
			default:
			case 0: mask = 0x3F; break;
			case 1: mask = 0x1F; break;
			case 2: mask = 0x2F; break;
			case 3: mask = 0x0F; break;
		}
		uint16_t outer = (_ex[0] & 0x38) << 1;
		SetCpuMemoryMapping(0x6000, 0x7FFF, (_prg[3] & mask) | outer, PrgMemoryType::PrgRom);
		SelectPrgPage(0, (_prg[0] & mask) | outer);
		SelectPrgPage(1, (_prg[1] & mask) | outer);
		SelectPrgPage(2, (_prg[2] & mask) | outer);
		SelectPrgPage(3, (0xFF & mask) | outer);

		SelectChrPage2x(0, _chr[0] * 2);
		SelectChrPage2x(1, _chr[1] * 2);
		SelectChrPage2x(2, _chr[6] * 2);
		SelectChrPage2x(3, _chr[7] * 2);

		if(_ex[2] & 2) SetMirroringType((_ex[2] & 1) ? MirroringType::ScreenBOnly : MirroringType::ScreenAOnly);
		else SetMirroringType((_ex[2] & 1) ? MirroringType::Vertical : MirroringType::Horizontal);
	}

protected:
	uint16_t GetPrgPageSize() override { return 0x2000; }
	uint16_t GetChrPageSize() override { return 0x0400; }
	uint16_t RegisterStartAddress() override { return 0x8000; }
	bool EnableCpuClockHook() override { return true; }
	bool EnableVramAddressHook() override { return true; }

	void InitMapper() override
	{
		memset(_prg, 0, sizeof(_prg));
		memset(_chr, 0, sizeof(_chr));
		memset(_ex, 0, sizeof(_ex));
		_irqReload = _irqEnabled = _irqPpuA12 = _irqAutoEnable = false;
		_irqLatch = _irqCount = 0;
		_irqCount16 = 0;
		_lastPpuAddr = 0;
		Sync();
	}

	void Serialize(Serializer& s) override
	{
		BaseMapper::Serialize(s);
		SVArray(_prg, 4); SVArray(_chr, 8); SVArray(_ex, 4);
		SV(_irqReload); SV(_irqEnabled); SV(_irqPpuA12); SV(_irqAutoEnable);
		SV(_irqLatch); SV(_irqCount); SV(_irqCount16); SV(_lastPpuAddr);
		if(!s.IsSaving()) Sync();
	}

	void WriteRegister(uint16_t addr, uint8_t value) override
	{
		if(addr < 0x9000) {
			_prg[addr & 3] = value;
			Sync();
		} else if(addr < 0xA000) {
			_ex[addr & 3] = value;
			Sync();
		} else if(addr < 0xC000) {
			uint8_t i = ((addr >> 10) & 4) | (addr & 3);
			_chr[i] = value;
			Sync();
		} else if(addr < 0xD000) {
			switch(addr & 0xF003) {
				case 0xC000:
					if(_irqAutoEnable) _irqEnabled = false;
					_irqCount16 = (_irqCount16 & 0xFF00) | value;
					_irqReload = true; ClearIrq(); break;
				case 0xC001:
					if(_irqAutoEnable) _irqEnabled = true;
					_irqCount16 = (_irqCount16 & 0x00FF) | ((int32_t)value << 8);
					_irqLatch = value; ClearIrq(); break;
				case 0xC002:
					_irqEnabled = value & 1; _irqPpuA12 = value & 2; _irqAutoEnable = value & 4; ClearIrq(); break;
				case 0xC003:
					_irqEnabled = value & 1; ClearIrq(); break;
			}
		}
	}

	void ProcessCpuClock() override
	{
		BaseProcessCpuClock();
		if(!_irqPpuA12 && _irqEnabled && _irqCount16 > 0) {
			_irqCount16--;
			if(_irqCount16 <= 0) RaiseIrq();
		}
	}

	void NotifyVramAddressChange(uint16_t addr) override
	{
		bool rise = !(_lastPpuAddr & 0x1000) && (addr & 0x1000);
		_lastPpuAddr = addr;
		if(_irqPpuA12 && rise) {
			if(!_irqCount || _irqReload) { _irqCount = _irqLatch; _irqReload = false; }
			else _irqCount--;
			if(!_irqCount && _irqEnabled) RaiseIrq();
		}
	}
};
