#pragma once
#include "pch.h"
#include "NES/BaseMapper.h"
#include "NES/NesConsole.h"
#include "NES/NesCpu.h"

class CoolGirl342 : public BaseMapper
{
private:
	uint32_t _prgBase = 0;
	uint32_t _prgMask = 0xF8 << 14;
	uint8_t _prgMode = 0;
	uint8_t _prg[5] = { 0, 0, 1, 0xFE, 0xFF }; // $6000,A,B,C,D (8 KiB units)

	uint32_t _chrMask = 0;
	uint8_t _chrMode = 0;
	uint16_t _chr[8] = { 0, 1, 2, 3, 4, 5, 6, 7 }; // A..H (1 KiB units)

	uint8_t _mapper = 0;
	uint8_t _flags = 0;
	uint8_t _mirroring = 0;
	uint8_t _sramPage = 0;
	bool _sramEnabled = false;
	bool _canWriteChr = false;
	bool _canWriteFlash = false;
	bool _fourScreen = false;
	bool _mapRomOn6000 = false;
	bool _lockout = false;

	uint8_t _mmc3Sel = 0;
	uint8_t _mmc3IrqLatch = 0;
	uint8_t _mmc3IrqCounter = 0;
	bool _mmc3IrqReload = false;
	bool _mmc3IrqEnabled = false;
	uint64_t _a12LowClock = 0;

	uint32_t MapPrg(uint8_t bank)
	{
		return (_prgBase >> 13) | (bank & (((~(_prgMask >> 13)) & 0xFE) | 1));
	}

	void SyncPrg()
	{
		uint32_t a = MapPrg(_prg[1]);
		uint32_t b = MapPrg(_prg[2]);
		uint32_t c = MapPrg(_prg[3]);
		uint32_t d = MapPrg(_prg[4]);

		switch(_prgMode & 7) {
			default:
			case 0:
				SelectPrgPage(0, a & ~1); SelectPrgPage(1, a | 1);
				SelectPrgPage(2, c & ~1); SelectPrgPage(3, c | 1);
				break;
			case 1:
				SelectPrgPage(0, c & ~1); SelectPrgPage(1, c | 1);
				SelectPrgPage(2, a & ~1); SelectPrgPage(3, a | 1);
				break;
			case 4:
				SelectPrgPage(0, a); SelectPrgPage(1, b); SelectPrgPage(2, c); SelectPrgPage(3, d);
				break;
			case 5:
				SelectPrgPage(0, c); SelectPrgPage(1, b); SelectPrgPage(2, a); SelectPrgPage(3, d);
				break;
			case 6: {
				uint32_t p = b & ~3;
				for(int i = 0; i < 4; i++) SelectPrgPage(i, p + i);
				break;
			}
			case 7: {
				uint32_t p = a & ~3;
				for(int i = 0; i < 4; i++) SelectPrgPage(i, p + i);
				break;
			}
		}

		if(_mapRomOn6000) {
			SetCpuMemoryMapping(0x6000, 0x7FFF, MapPrg(_prg[0]), PrgMemoryType::PrgRom);
		} else if(_sramEnabled) {
			SetCpuMemoryMapping(0x6000, 0x7FFF, _sramPage & 3, PrgMemoryType::WorkRam);
		} else {
			RemoveCpuMemoryMapping(0x6000, 0x7FFF);
		}
	}

	uint16_t MaskChr(uint16_t page)
	{
		// CoolGirl CHR mask covers address lines A18-A13. CHR pages here are 1 KiB,
		// so these correspond to page bits 8..3. A zero mask leaves the full 512 KiB visible.
		uint16_t blocked = (uint16_t)((_chrMask >> 10) & 0x1F8);
		return page & ~blocked;
	}

	void SyncChr()
	{
		uint16_t c[8];
		for(int i = 0; i < 8; i++) c[i] = MaskChr(_chr[i]);

		switch(_chrMode & 7) {
			default:
			case 0:
				SelectChrPage8x(0, c[0] & ~7, ChrMemoryType::ChrRam);
				break;
			case 1:
				// Mapper 163 latch mode is handled as a stable 4 KiB/4 KiB mapping here.
				SelectChrPage4x(0, c[0] & ~3, ChrMemoryType::ChrRam);
				SelectChrPage4x(1, c[0] & ~3, ChrMemoryType::ChrRam);
				break;
			case 2:
				SelectChrPage2x(0, c[0] & ~1, ChrMemoryType::ChrRam);
				SelectChrPage2x(1, c[2] & ~1, ChrMemoryType::ChrRam);
				SelectChrPage(4, c[4], ChrMemoryType::ChrRam);
				SelectChrPage(5, c[5], ChrMemoryType::ChrRam);
				SelectChrPage(6, c[6], ChrMemoryType::ChrRam);
				SelectChrPage(7, c[7], ChrMemoryType::ChrRam);
				break;
			case 3:
				SelectChrPage(0, c[4], ChrMemoryType::ChrRam);
				SelectChrPage(1, c[5], ChrMemoryType::ChrRam);
				SelectChrPage(2, c[6], ChrMemoryType::ChrRam);
				SelectChrPage(3, c[7], ChrMemoryType::ChrRam);
				SelectChrPage2x(2, c[0] & ~1, ChrMemoryType::ChrRam);
				SelectChrPage2x(3, c[2] & ~1, ChrMemoryType::ChrRam);
				break;
			case 4:
				SelectChrPage4x(0, c[0] & ~3, ChrMemoryType::ChrRam);
				SelectChrPage4x(1, c[4] & ~3, ChrMemoryType::ChrRam);
				break;
			case 5:
				SelectChrPage4x(0, c[0] & ~3, ChrMemoryType::ChrRam);
				SelectChrPage4x(1, c[4] & ~3, ChrMemoryType::ChrRam);
				break;
			case 6:
				SelectChrPage2x(0, c[0] & ~1, ChrMemoryType::ChrRam);
				SelectChrPage2x(1, c[2] & ~1, ChrMemoryType::ChrRam);
				SelectChrPage2x(2, c[4] & ~1, ChrMemoryType::ChrRam);
				SelectChrPage2x(3, c[6] & ~1, ChrMemoryType::ChrRam);
				break;
			case 7:
				for(int i = 0; i < 8; i++) SelectChrPage(i, c[i], ChrMemoryType::ChrRam);
				break;
		}
	}

	void SyncMirroring()
	{
		if(_fourScreen) {
			SetMirroringType(MirroringType::FourScreens);
			return;
		}
		switch(_mirroring & 3) {
			case 0: SetMirroringType(MirroringType::Vertical); break;
			case 1: SetMirroringType(MirroringType::Horizontal); break;
			case 2: SetMirroringType(MirroringType::ScreenAOnly); break;
			case 3: SetMirroringType(MirroringType::ScreenBOnly); break;
		}
	}

	void Sync()
	{
		SyncPrg();
		SyncChr();
		SyncMirroring();
	}

	void WriteConfig(uint16_t addr, uint8_t v)
	{
		if(_lockout) return;

		// Native CoolGirl register layout ($5000-$5FFF, mirrored every 8 bytes).
		switch(addr & 7) {
			case 0:
				// PRG base A29-A22
				_prgBase = (_prgBase & 0x003FFFFF) | ((uint32_t)v << 22);
				break;
			case 1:
				// PRG base A21-A14
				_prgBase = (_prgBase & ~0x003FC000) | ((uint32_t)v << 14);
				break;
			case 2:
				// CHR mask A18 + PRG mask A20-A14
				_chrMask = (_chrMask & ~(1u << 18)) | ((uint32_t)(v >> 7) << 18);
				_prgMask = (_prgMask & ~(0x7Fu << 14)) | ((uint32_t)(v & 0x7F) << 14);
				break;
			case 3:
				// PRG mode + CHR bank A bits 7-3
				_prgMode = (v >> 5) & 7;
				_chr[0] = (_chr[0] & ~0xF8u) | ((uint16_t)(v & 0x1F) << 3);
				break;
			case 4:
				// CHR mode + CHR mask A17-A13
				_chrMode = (v >> 5) & 7;
				_chrMask = (_chrMask & ~(0x1Fu << 13)) | ((uint32_t)(v & 0x1F) << 13);
				break;
			case 5:
				// CHR bank A bit 8 + PRG bank A bits 5-1 + WRAM page
				_chr[0] = (_chr[0] & ~0x100u) | ((uint16_t)(v >> 7) << 8);
				_prg[1] = (_prg[1] & ~0x3Eu) | ((v >> 2) & 0x1F) << 1;
				_sramPage = v & 3;
				break;
			case 6:
				// Flags 2-0 + mapper code bits 4-0
				_flags = (v >> 5) & 7;
				_mapper = (_mapper & 0x20) | (v & 0x1F);
				break;
			case 7:
				// Lock, mapper bit 5, 4-screen, mirroring, flash/CHR/WRAM enables
				_lockout = (v & 0x80) != 0;
				_mapper = (_mapper & 0x1F) | ((v & 0x40) >> 1);
				_fourScreen = (v & 0x20) != 0;
				_mirroring = (v >> 3) & 3;
				_canWriteFlash = (v & 0x04) != 0;
				_canWriteChr = (v & 0x02) != 0;
				_sramEnabled = (v & 0x01) != 0;

				// Special initialization required by a few internal mapper modes.
				if(_mapper == 0x11) _prg[2] = 0xFD;
				if(_mapper == 0x17) _mapRomOn6000 = true;
				if(_mapper == 0x0E) _prg[2] = 1;
				break;
		}
		Sync();
	}

	bool IsA12RisingEdge(uint16_t addr)
	{
		if(addr & 0x1000) {
			bool rising = _a12LowClock > 0 && (_console->GetMasterClock() - _a12LowClock) >= 3;
			_a12LowClock = 0;
			return rising;
		} else if(_a12LowClock == 0) {
			_a12LowClock = _console->GetMasterClock();
		}
		return false;
	}

	void ResetRegisters()
	{
		_prgBase = 0;
		_prgMask = 0xF8 << 14;
		_prgMode = 0;
		_prg[0] = 0; _prg[1] = 0; _prg[2] = 1; _prg[3] = 0xFE; _prg[4] = 0xFF;
		_chrMask = 0;
		_chrMode = 0;
		for(int i = 0; i < 8; i++) _chr[i] = i;
		_mapper = 0;
		_flags = 0;
		_mirroring = 0;
		_sramPage = 0;
		_sramEnabled = false;
		_canWriteChr = false;
		_canWriteFlash = false;
		_fourScreen = false;
		_mapRomOn6000 = false;
		_lockout = false;
		_mmc3Sel = 0;
		_mmc3IrqLatch = 0;
		_mmc3IrqCounter = 0;
		_mmc3IrqReload = false;
		_mmc3IrqEnabled = false;
		_a12LowClock = 0;
	}

protected:
	uint16_t GetPrgPageSize() override { return 0x2000; }
	uint16_t GetChrPageSize() override { return 0x0400; }
	uint32_t GetChrRamSize() override { return 0x80000; } // hardware supports up to 512 KiB
	uint32_t GetWorkRamSize() override { return 0x8000; } // 4 x 8 KiB
	uint32_t GetNametableCount() override { return 4; }
	uint16_t RegisterStartAddress() override { return 0x5000; }
	uint16_t RegisterEndAddress() override { return 0xFFFF; }
	bool EnableVramAddressHook() override { return true; }

	void InitMapper() override
	{
		ResetRegisters();
		AddRegisterRange(0x5000, 0x5FFF, MemoryOperation::Write);
		Sync();
	}

	void Serialize(Serializer& s) override
	{
		BaseMapper::Serialize(s);
		SV(_prgBase); SV(_prgMask); SV(_prgMode); SVArray(_prg, 5);
		SV(_chrMask); SV(_chrMode); SVArray(_chr, 8);
		SV(_mapper); SV(_flags); SV(_mirroring); SV(_sramPage);
		SV(_sramEnabled); SV(_canWriteChr); SV(_canWriteFlash); SV(_fourScreen); SV(_mapRomOn6000); SV(_lockout);
		SV(_mmc3Sel); SV(_mmc3IrqLatch); SV(_mmc3IrqCounter); SV(_mmc3IrqReload); SV(_mmc3IrqEnabled); SV(_a12LowClock);
		if(!s.IsSaving()) Sync();
	}

	void WriteRegister(uint16_t addr, uint8_t value) override
	{
		if(addr >= 0x5000 && addr <= 0x5FFF) {
			WriteConfig(addr, value);
			return;
		}

		// Common internal mapper modes.  The menu itself runs in the power-on
		// NROM-style mode; these handlers cover the most common launched games.
		if(_mapper == 0x00) return; // NROM

		if(_mapper == 0x01) { // UxROM / mapper 2 family
			_prg[1] = (_prg[1] & 1) | ((value & 0x1F) << 1);
			SyncPrg();
			return;
		}

		if(_mapper == 0x02) { // CNROM
			_chr[0] = (_chr[0] & 0x100) | ((value & 0x1F) << 3);
			SyncChr();
			return;
		}

		if(_mapper == 0x14) { // MMC3/MMC6 family
			switch(addr & 0xE001) {
				case 0x8000:
					_mmc3Sel = value & 7;
					_prgMode = (value & 0x40) ? 5 : 4;
					_chrMode = (value & 0x80) ? 3 : 2;
					Sync();
					break;
				case 0x8001:
					switch(_mmc3Sel) {
						case 0: _chr[0] = value & 0xFE; break;
						case 1: _chr[2] = value & 0xFE; break;
						case 2: _chr[4] = value; break;
						case 3: _chr[5] = value; break;
						case 4: _chr[6] = value; break;
						case 5: _chr[7] = value; break;
						case 6: _prg[1] = value; break;
						case 7: _prg[2] = value; break;
					}
					Sync();
					break;
				case 0xA000:
					if(!_fourScreen) {
						_mirroring = value & 1;
						SyncMirroring();
					}
					break;
				case 0xC000:
					_mmc3IrqLatch = value;
					break;
				case 0xC001:
					_mmc3IrqCounter = 0;
					_mmc3IrqReload = true;
					break;
				case 0xE000:
					_mmc3IrqEnabled = false;
					_console->GetCpu()->ClearIrqSource(IRQSource::External);
					break;
				case 0xE001:
					_mmc3IrqEnabled = true;
					break;
			}
		}
	}

public:
	void Reset(bool softReset) override
	{
		BaseMapper::Reset(softReset);
		ResetRegisters();
		Sync();
	}

	void NotifyVramAddressChange(uint16_t addr) override
	{
		if(_mapper != 0x14 || !IsA12RisingEdge(addr)) return;

		if(_mmc3IrqCounter == 0 || _mmc3IrqReload) {
			_mmc3IrqCounter = _mmc3IrqLatch;
		} else {
			_mmc3IrqCounter--;
		}

		if(_mmc3IrqCounter == 0 && _mmc3IrqEnabled) {
			_console->GetCpu()->SetIrqSource(IRQSource::External);
		}
		_mmc3IrqReload = false;
	}
};
