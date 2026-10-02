#pragma once
#include "pch.h"
#include "NES/BaseMapper.h"

class CoolGirl342 : public BaseMapper
{
private:
	uint32_t _prgBase = 0;
	uint32_t _prgMask = 0xF8 << 14;
	uint8_t _prgMode = 0;
	uint8_t _prg[5] = { 0, 0, 1, 0xFE, 0xFF }; // $6000,A,B,C,D
	uint32_t _chrMask = 0;
	uint8_t _chrMode = 0;
	uint16_t _chr[8] = { 0,1,2,3,4,5,6,7 };
	uint8_t _mapper = 0;
	uint8_t _flags = 0;
	uint8_t _mirroring = 0;
	bool _sramEnabled = false;
	bool _lockout = false;

	uint16_t MapPrg(uint8_t bank)
	{
		return (uint16_t)((_prgBase >> 13) | (bank & (((~(_prgMask >> 13)) & 0xFE) | 1)));
	}

	void SyncPrg()
	{
		uint16_t a = MapPrg(_prg[1]);
		uint16_t b = MapPrg(_prg[2]);
		uint16_t c = MapPrg(_prg[3]);
		uint16_t d = MapPrg(_prg[4]);
		switch(_prgMode & 7) {
			default:
			case 0:
				SelectPrgPage(0, a & ~1); SelectPrgPage(1, a | 1);
				SelectPrgPage(2, c & ~1); SelectPrgPage(3, c | 1); break;
			case 1:
				SelectPrgPage(0, c & ~1); SelectPrgPage(1, c | 1);
				SelectPrgPage(2, a & ~1); SelectPrgPage(3, a | 1); break;
			case 4:
				SelectPrgPage(0, a); SelectPrgPage(1, b); SelectPrgPage(2, c); SelectPrgPage(3, d); break;
			case 5:
				SelectPrgPage(0, c); SelectPrgPage(1, b); SelectPrgPage(2, a); SelectPrgPage(3, d); break;
			case 6: {
				uint16_t p = b & ~3; for(int i=0;i<4;i++) SelectPrgPage(i, p+i); break;
			}
			case 7: {
				uint16_t p = a & ~3; for(int i=0;i<4;i++) SelectPrgPage(i, p+i); break;
			}
		}
		if(_sramEnabled) SetCpuMemoryMapping(0x6000, 0x7FFF, 0, PrgMemoryType::WorkRam);
		else RemoveCpuMemoryMapping(0x6000, 0x7FFF);
	}

	void SyncChr()
	{
		switch(_chrMode & 7) {
			default:
			case 0: SelectChrPage8x(0, (_chr[0] >> 3) * 8); break;
			case 2:
				SelectChrPage2x(0, (_chr[0] >> 1) * 2); SelectChrPage2x(1, (_chr[2] >> 1) * 2);
				SelectChrPage(4, _chr[4]); SelectChrPage(5, _chr[5]); SelectChrPage(6, _chr[6]); SelectChrPage(7, _chr[7]); break;
			case 3:
				SelectChrPage(0,_chr[4]); SelectChrPage(1,_chr[5]); SelectChrPage(2,_chr[6]); SelectChrPage(3,_chr[7]);
				SelectChrPage2x(2,(_chr[0]>>1)*2); SelectChrPage2x(3,(_chr[2]>>1)*2); break;
			case 4: SelectChrPage4x(0, (_chr[0] >> 2) * 4); SelectChrPage4x(1, (_chr[4] >> 2) * 4); break;
			case 6:
				SelectChrPage2x(0,(_chr[0]>>1)*2); SelectChrPage2x(1,(_chr[2]>>1)*2); SelectChrPage2x(2,(_chr[4]>>1)*2); SelectChrPage2x(3,(_chr[6]>>1)*2); break;
			case 7: for(int i=0;i<8;i++) SelectChrPage(i,_chr[i]); break;
		}
	}

	void Sync()
	{
		SyncPrg(); SyncChr();
		switch(_mirroring & 3) {
			case 0: SetMirroringType(MirroringType::Vertical); break;
			case 1: SetMirroringType(MirroringType::Horizontal); break;
			case 2: SetMirroringType(MirroringType::ScreenAOnly); break;
			case 3: SetMirroringType(MirroringType::ScreenBOnly); break;
		}
	}

	void WriteConfig(uint16_t addr, uint8_t v)
	{
		if(_lockout) return;
		switch(addr & 7) {
			case 0:
				_prgBase = (_prgBase & ~0x00180000) | ((uint32_t)(v & 0x70) << 15);
				_prgMask = (uint32_t)((v & 0x0F) ^ 0x0F) << 18;
				_sramEnabled = (v & 0x80) != 0; break;
			case 1:
				_prgBase = (_prgBase & ~0x00060000) | ((uint32_t)(v & 0x03) << 17);
				_prgMode = (v >> 2) & 7; _prg[1] = (_prg[1] & ~7) | ((v >> 5) & 7); break;
			case 2:
				_prg[1] = (_prg[1] & 7) | ((v & 3) << 3); _prg[3] = (v >> 2) & 0x1F; _mirroring = v >> 7; break;
			case 3:
				_chr[0] = (_chr[0] & ~0x38) | ((v & 7) << 3); _chrMask = ((v >> 3) & 7) ^ 7; _chrMode = (v >> 6) & 3; break;
			case 4:
				_chr[0] = (_chr[0] & 0x38) | ((v & 0x0F) << 6); _mapper = (_mapper & ~0x0F) | (v >> 4); break;
			case 5:
				_mapper = (_mapper & 0x0F) | ((v & 3) << 4); _flags = (v >> 2) & 0x1F; _lockout = (v & 0x80) != 0; break;
			case 6: _flags = (_flags & 0x1F) | ((v & 7) << 5); break;
			case 7: break;
		}
		Sync();
	}

protected:
	uint16_t GetPrgPageSize() override { return 0x2000; }
	uint16_t GetChrPageSize() override { return 0x0400; }
	uint32_t GetChrRamSize() override { return 0x40000; }
	uint32_t GetWorkRamSize() override { return 0x8000; }
	uint16_t RegisterStartAddress() override { return 0x5000; }
	uint16_t RegisterEndAddress() override { return 0xFFFF; }

	void InitMapper() override
	{
		AddRegisterRange(0x5000, 0x5FFF, MemoryOperation::Write);
		Sync();
	}

	void Serialize(Serializer& s) override
	{
		BaseMapper::Serialize(s);
		SV(_prgBase); SV(_prgMask); SV(_prgMode); SVArray(_prg,5);
		SV(_chrMask); SV(_chrMode); SVArray(_chr,8); SV(_mapper); SV(_flags); SV(_mirroring); SV(_sramEnabled); SV(_lockout);
		if(!s.IsSaving()) Sync();
	}

	void WriteRegister(uint16_t addr, uint8_t value) override
	{
		if(addr >= 0x5000 && addr <= 0x5FFF) { WriteConfig(addr, value); return; }
		// Common internal mapper modes used by CoolGirl menus/containers.
		if(_mapper == 0x00) return; // NROM
		if(_mapper == 0x01) { _prg[1] = (_prg[1] & 1) | ((value & 0x1F) << 1); SyncPrg(); return; } // UxROM
		if(_mapper == 0x02) { _chr[0] = (value & 0x1F) << 3; SyncChr(); return; } // CNROM
		if(_mapper == 0x14) { // MMC3-style banking subset
			static uint8_t sel = 0;
			if((addr & 0xE001) == 0x8000) { sel = value & 7; _prgMode = (value & 0x40) ? 5 : 4; _chrMode = (value & 0x80) ? 3 : 2; }
			else if((addr & 0xE001) == 0x8001) {
				switch(sel) { case 0:_chr[0]=value;break; case 1:_chr[2]=value;break; case 2:_chr[4]=value;break; case 3:_chr[5]=value;break; case 4:_chr[6]=value;break; case 5:_chr[7]=value;break; case 6:_prg[1]=value;break; case 7:_prg[2]=value;break; }
			} else if((addr & 0xE001) == 0xA000) _mirroring = value & 1;
			Sync();
		}
	}
};
