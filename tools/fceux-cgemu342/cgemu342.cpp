#include "cgemu342.h"
#include "types.h"
#include "driver.h"
#include "fceu.h"

#include <windows.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <string>

extern uint8 *RAM;
FCEUGI *FCEUI_LoadGame(const char *name, int OverwriteVidMode, bool silent);

static std::string g_menuPath;
static std::string g_pendingPath;
static bool g_menuActive = false;
static bool g_launchGuard = false;

static uint16_t rd16(const unsigned char *p) { return (uint16_t)p[0] | ((uint16_t)p[1] << 8); }
static uint32_t rd32(const unsigned char *p) { return (uint32_t)p[0] | ((uint32_t)p[1]<<8) | ((uint32_t)p[2]<<16) | ((uint32_t)p[3]<<24); }
static uint64_t rd64(const unsigned char *p) { return (uint64_t)rd32(p) | ((uint64_t)rd32(p+4)<<32); }

static bool footer(const char *path, uint32_t &count, uint64_t &dirOff, uint64_t &dirSize)
{
    FILE *f=fopen(path,"rb"); if(!f) return false;
    if(_fseeki64(f,0,SEEK_END)!=0){fclose(f);return false;}
    __int64 sz=_ftelli64(f); if(sz<48){fclose(f);return false;}
    if(_fseeki64(f,sz-48,SEEK_SET)!=0){fclose(f);return false;}
    unsigned char b[48]; bool ok=fread(b,1,48,f)==48; fclose(f);
    if(!ok || memcmp(b,"CGEMU342",8)!=0) return false;
    if(rd32(b+8)!=1) return false;
    count=rd32(b+12); dirOff=rd64(b+16); dirSize=rd64(b+24);
    return count>0 && dirSize >= (uint64_t)count*288ULL && dirOff+dirSize <= (uint64_t)(sz-48);
}

static std::string safeName(const unsigned char *p,size_t n)
{
    std::string s;
    for(size_t i=0;i<n && p[i];++i){ char c=(char)p[i]; if(strchr("<>:\"/\\|?*",c)) c='_'; s+=c; }
    return s.empty()?"game":s;
}

static bool extract(unsigned id,std::string &out)
{
    uint32_t count=0; uint64_t d=0,ds=0;
    if(g_menuPath.empty() || !footer(g_menuPath.c_str(),count,d,ds) || id>=count) return false;
    FILE *f=fopen(g_menuPath.c_str(),"rb"); if(!f) return false;
    if(_fseeki64(f,(__int64)(d+(uint64_t)id*288ULL),SEEK_SET)!=0){fclose(f);return false;}
    unsigned char e[288]; if(fread(e,1,288,f)!=288){fclose(f);return false;}
    uint64_t off=rd64(e), len=rd64(e+8); uint16_t fmt=rd16(e+16);
    char temp[MAX_PATH]={0}; if(!GetTempPathA(MAX_PATH,temp)){fclose(f);return false;}
    std::string dir=std::string(temp)+"CGEMU342_FCEUX"; CreateDirectoryA(dir.c_str(),NULL);
    char idbuf[32]; sprintf(idbuf,"%03u_",id);
    out=dir+"\\"+idbuf+safeName(e+24,128)+(fmt==3?".unf":".nes");
    if(_fseeki64(f,(__int64)off,SEEK_SET)!=0){fclose(f);return false;}
    FILE *o=fopen(out.c_str(),"wb"); if(!o){fclose(f);return false;}
    unsigned char buf[65536]; uint64_t left=len;
    while(left){ size_t want=left>sizeof(buf)?sizeof(buf):(size_t)left; size_t got=fread(buf,1,want,f); if(!got || fwrite(buf,1,got,o)!=got){fclose(o);fclose(f);DeleteFileA(out.c_str());return false;} left-=got; }
    fclose(o); fclose(f); return true;
}

void CGEMU342_OnRomLoaded(const char *name)
{
    uint32_t c=0; uint64_t d=0,ds=0;
    if(name && footer(name,c,d,ds)){ g_menuPath=name; g_menuActive=true; g_launchGuard=false; }
    else g_menuActive=false;
}

void CGEMU342_PollMailbox()
{
    if(!g_menuActive || !RAM) return;
    unsigned char magic=RAM[0x7F2];
    if(magic==0xA5 && !g_launchGuard){
        g_launchGuard=true;
        unsigned id=(unsigned)RAM[0x7F0] | ((unsigned)RAM[0x7F1]<<8);
        RAM[0x7F2]=0;
        std::string p; if(extract(id,p)){ g_pendingPath=p; g_menuActive=false; }
    } else if(magic!=0xA5) g_launchGuard=false;
}

void CGEMU342_TryDeferredLoad()
{
    if(g_pendingPath.empty()) return;
    std::string p=g_pendingPath; g_pendingPath.clear();
    FCEUI_LoadGame(p.c_str(),1,false);
}
