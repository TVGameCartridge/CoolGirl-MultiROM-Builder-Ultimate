LOADER_REG_0 .rs 1
LOADER_REG_1 .rs 1
LOADER_REG_2 .rs 1
LOADER_REG_3 .rs 1
LOADER_REG_4 .rs 1
LOADER_REG_5 .rs 1
LOADER_REG_6 .rs 1
LOADER_REG_7 .rs 1
LOADER_CHR_START_H .rs 1
LOADER_CHR_START_L .rs 1
LOADER_CHR_START_S .rs 1
LOADER_CHR_LEFT .rs 1
LOADER_GAME_SAVE .rs 1
LOADER_GAME_SAVE_BANK .rs 1
LOADER_GAME_SAVE_SUPERBANK .rs 1

loader:
    sei
    cld

    ; 1. Seadistame mälupiirkonna (Superbank)
    lda LOADER_REG_1
    sta $5001
    lda LOADER_REG_0
    sta $5000

    ; 2. Aktiveerime mapperi ja põhiregistrid
    lda LOADER_REG_2
    sta $5002
    lda LOADER_REG_3
    sta $5003
    lda LOADER_REG_4
    sta $5004
    lda LOADER_REG_5
    sta $5005
    lda LOADER_REG_6
    sta $5006
    lda LOADER_REG_7
    sta $5007

    ; --- SPETSIIFILISED PARANDUSED ---
    lda LOADER_REG_2

    cmp #20 ; Mapper 20 (SF3)
    beq .fix_sf3
    cmp #35 ; Mapper 35 (SF3/Yoko)
    beq .fix_sf3
    cmp #14 ; Mapper 90
    beq .fix_90
    jmp .skip_fixes


.fix_sf3:
    ; --- JY COMPANY / SF3 "WAKE UP" SEQUENCE ---
    
    ; 1. Keela IRQ ja lülita välja igasugune mapi-poolne katkestus
    lda #$00
    sta $E000         ; MMC3 IRQ Disable
    sta $5003         ; Outer Bank Control (Nullimine on oluline!)

    ; 2. Aktiveeri WRAM ($6000) ja vali režiim
    lda #$80          ; Enable RAM, Write Protect OFF
    sta $A001
    
    lda #$01          ; Mirroring: Horizontal
    sta $A000

    ; 3. --- CHR-RAM LUKUST VABASTAMINE ---
    ; JY Company kiibid vajavad, et CHR registrid 0-5 saaksid väärtused.
    ; Ilma selleta ei pruugi graafika RAM üldse kättesaadav olla.
    ldx #$00
.sf3_init_loop:
    stx $8000
    txa               ; Paneme panga numbri (0, 1, 2, 3...)
    sta $8001
    inx
    cpx #$06
    bne .sf3_init_loop

    ; 4. Spetsiifiline Yoko/Cony register (Mapper 35/20 variant)
    lda #$00
    sta $4100         ; Mõned SF3-d ootavad siia nulli

    jmp .skip_fixes
.fix_90:
    ; Mapper 90 vajab kindlaid PRG aadresse alguseks
    lda #$00
    sta $8000
    lda #$01
    sta $8001
    lda #$00
    sta $D001
    sta $D003

.skip_fixes:
    ; Puhastame registrid, et MMC3 oleks "puhas leht"
    lda #$00
    sta $8000
    sta $8001
    sta $E000         ; IRQ disable (igaks juhuks uuesti)

loader_clean_and_start:
    ; 1. Puhastame RAM-i ($0000-$07FF)
    lda #$00
    sta <$00
    sta <$01
    ldy #$00
.ram_loop:
    sta [$00], y
    iny
    bne .ram_loop
    inc <$01
    lda <$01
    cmp #$08    
    bne .ram_loop

; --- KRIITILINE ETTEVALMISTUS SF3-LE ---
    lda #$00
    sta $2000         ; NMI off
    sta $2001         ; Rendering off (must ekraan)
    
    ; Ootame vblanki, et PPU oleks stabiilne
.v_wait:
    bit $2002
    bpl .v_wait

    ; Stacki puhastus - piraatmängud on selle suhtes tundlikud
    ldx #$FF
    txs
    
    ; Nullime peamised registrid
    lda #$00
    tax
    tay

    ; HÜPE MÄNGU (Reset vektorilt)
    jmp [$FFFC]

; ... (siin lõppeb sinu jmp [$FFFC] rutiin) ...

; --- NEED PEAVAD OLEMA SIIN, ET TEISED FAILID NEID NÄEKSID ---

load_all_chr_banks:
    lda #0
    sta <CHR_BANK
    sta <PRG_BANK
    sta <COPY_SOURCE_ADDR
    lda <LOADER_CHR_START_L
    sta <PRG_SUPERBANK
    lda <LOADER_CHR_START_H
    sta <PRG_SUPERBANK+1
.loop:
    lda <LOADER_CHR_LEFT
    beq .done
    dec <LOADER_CHR_LEFT
    
    jsr sync_banks
    
    lda <LOADER_CHR_START_S
    sta <COPY_SOURCE_ADDR+1
    
    jsr load_chr
    
    lda <LOADER_CHR_START_S
    clc
    adc #$20
    sta <LOADER_CHR_START_S
    cmp #$C0 
    bne .no_overflow
    
    lda #$80
    sta <LOADER_CHR_START_S
    inc <PRG_SUPERBANK
    bne .no_overflow
    inc <PRG_SUPERBANK+1
.no_overflow:
    inc <CHR_BANK
    jmp .loop
.done:
    jsr banking_init
    rts

load_chr:
    jsr enable_chr_write 
    lda #$00
    sta $2006 ; PPUADDR High
    sta $2006 ; PPUADDR Low
    ldy #$00
    ldx #$20  ; 8192 baiti
.inner_loop:
    lda [COPY_SOURCE_ADDR], y
    sta $2007 ; PPUDATA
    iny
    bne .inner_loop
    inc <COPY_SOURCE_ADDR+1
    dex
    bne .inner_loop
    jsr disable_chr_write
    rts