PALETTE_CACHE     .rs 32 ; temporary memory for palette, for dimming
  ; cursors target coordinates
SPRITE_0_X_TARGET .rs 1
SPRITE_1_X_TARGET .rs 1
SPRITE_Y_TARGET .rs 1
  ; variables for game name drawing
TEXT_DRAW_GAME .rs 2
TEXT_DRAW_ROW .rs 1
SCROLL_LINES .rs 2 ; current scroll line
SCROLL_LINES_MODULO .rs 1 ; current scroll line % 30
LAST_LINE_MODULO .rs 1
LAST_LINE_GAME .rs 2
SCROLL_FINE .rs 1 ; fine scroll position
SCROLL_LINES_TARGET .rs 2 ; scrolling target
STAR_SPAWN_TIMER .rs 1 ; stars spawn timer
STAR_SPAWN_COUNTER .rs 1 ; stars spawn counter
  ; for build info
CHR_RAM_SIZE .rs 1 ; CHR RAM size 8*2^xKB
LAST_ATTRIBUTE_ADDRESS .rs 1 ; to prevent duplicate writes
SCHEDULE_PRINT_FIRST .rs 1
SCHEDULE_PRINT_LAST .rs 1
  ; flag to lock scrolling at zero
SCROLL_LOCK .rs 1
  ; flag that save warning message is active
SAVE_WARNED .rs 1

  ; constants
CHARS_PER_LINE .equ 32
LINES_PER_SCREEN .equ 30

SPRITE_0_Y    .equ SPRITES + 0
SPRITE_0_TILE .equ SPRITES + 1
SPRITE_0_ATTR .equ SPRITES + 2
SPRITE_0_X    .equ SPRITES + 3
SPRITE_1_Y    .equ SPRITES + 4
SPRITE_1_TILE .equ SPRITES + 5
SPRITE_1_ATTR .equ SPRITES + 6
SPRITE_1_X    .equ SPRITES + 7

waitblank:
  pha
  tya
  pha
  txa
  pha
  bit PPUSTATUS ; reset vblank bit
.loop:
  lda PPUSTATUS ; load A with value at location PPUSTATUS
  bpl .loop ; if bit 7 is not set (not VBlank) keep checking

  ; updating sprites
  jsr sprite_dma_copy
  jsr scroll_fix
  ; scrolling
  lda <SCROLL_LOCK
  bne .skip_scrolling
  jsr move_scrolling
.skip_scrolling:
  ; moving cursors
  jsr move_cursors
  ; reading controller
  jsr read_controller
  ; stars on the background
  .if STARS!=0
  jsr stars
  .endif

  pla
  tax
  pla
  tay
  pla
  rts

waitblank_simple:
  pha
  bit PPUSTATUS
.loop:
  lda PPUSTATUS  ; load A with value at location PPUSTATUS
  bpl .loop  ; if bit 7 is not set (not VBlank) keep checking
  pla
  rts

waitblank_x:
  ; for for v-blank X times
  cpy #0
  bne .loop
  rts
.loop:
  jsr waitblank
  dex
  bne .loop
  rts

scroll_fix:
  pha
  tya
  pha

  bit $2002
  lda #0
  sta $2005    ; X-scroll = 0
  sta $2005    ; Y-scroll = 0
  
  lda #%10001000 ; NMI sees, Nametable $2000
  sta $2000      ; PPUCTRL (mitte $2008!)
  
  pla
  tay
  pla
  rts

screen_wrap_down:
  rts

screen_wrap_up:
  rts

load_base_chr:
  ; loading CHR
  lda #BANK(chr_data) / 2 ; bank with CHR
  jsr select_prg_bank
  lda #LOW(chr_data)
  sta COPY_SOURCE_ADDR
  lda #HIGH(chr_data)
  sta COPY_SOURCE_ADDR+1
  jsr load_chr
  rts

preload_palette:
  ; loading palette into palette cache
  ldy #0
.loop:
  lda [COPY_SOURCE_ADDR], y
  sta PALETTE_CACHE, y
  iny
  cpy #32
  bne .loop
  rts

preload_base_palette:
  ; loading palette into palette cache
  lda #BANK(tilepal) / 2 ; bank with palette
  jsr select_prg_bank
  lda #LOW(tilepal)
  sta COPY_SOURCE_ADDR
  lda #HIGH(tilepal)
  sta COPY_SOURCE_ADDR+1
  jsr preload_palette
  rts

  ; loading palette from cache to PPU
load_palette:
  jsr waitblank_simple
  lda #LOW(PALETTE_CACHE)
  sta <COPY_SOURCE_ADDR
  lda #HIGH(PALETTE_CACHE)
  sta <COPY_SOURCE_ADDR+1
  lda #$3F
  sta $2006
  lda #$00
  sta $2006
  ldy #$00
  ldx #32
.loop:
  lda [COPY_SOURCE_ADDR], y
  sta $2007
  iny
  dex
  bne .loop
  jsr scroll_fix
  rts

;load_base_pal:
  ; loading palette into $3F00 of PPU
  ;lda #$3F
  ;sta PPUADDR
  ;lda #$00
  ;sta PPUADDR
  ;ldx #$00
;.loop:
  ;lda tilepal, x
  ;sta PPUDATA
  ;inx
  ;cpx #32
  ;bne .loop
  ;rts

dim:
  ; dimming preloaded palette
  ldx #0
.loop:
  lda PALETTE_CACHE, x
  sec
  sbc #$10
  bpl .not_minus
  lda #$1D  
.not_minus:
  cmp #$0D
  bne .not_very_black
  lda #$1D
.not_very_black:
  sta PALETTE_CACHE, x
  inx
  cpx #32
  bne .loop
  rts

  ; dimming base palette in
dim_base_palette_in:
  ;lda BUTTONS
  ;bne .done ; skip if any button pressed
  .if ENABLE_DIM_IN!=0
  .if DIM_IN_DELAY <= 0
  .fail DIM_IN_DELAY must be > 0
  .endif
  jsr preload_base_palette
  jsr dim
  jsr dim
  jsr dim
  jsr load_palette
  ldx #DIM_IN_DELAY
  jsr waitblank_x
  ;lda BUTTONS
  ;bne .done ; skip if any button pressed
  jsr preload_base_palette
  jsr dim
  jsr dim
  jsr load_palette
  ldx #DIM_IN_DELAY
  jsr waitblank_x
  ;lda BUTTONS
  ;bne .done ; skip if any button pressed
  jsr preload_base_palette
  jsr dim
  jsr load_palette
  ldx #DIM_IN_DELAY
  jsr waitblank_x
  .endif
.done:
  jsr preload_base_palette
  jsr load_palette
  jsr waitblank
  rts

  ; dimming base palette out in
dim_base_palette_out:
  .if ENABLE_DIM_OUT!=0
  .if DIM_OUT_DELAY <= 0
  .fail DIM_OUT_DELAY must be > 0
  .endif
  jsr preload_base_palette
  jsr dim
  jsr load_palette
  ldx #DIM_OUT_DELAY
  jsr waitblank_x
  jsr preload_base_palette
  jsr dim
  jsr dim
  jsr load_palette
  ldx #DIM_OUT_DELAY
  jsr waitblank_x
  jsr preload_base_palette
  jsr dim
  jsr dim
  jsr dim
  jsr load_palette
  ldx #DIM_OUT_DELAY
  jsr waitblank_x
  .endif
  jsr load_black
  jsr waitblank
  rts

  ; loading empty black palette into $3F00 of PPU
load_black:
  ; waiting for vblank
  ; need even if rendering is disabled
  ; to prevent lines on black screen
  jsr waitblank_simple
  lda #$3F
  sta PPUADDR
  lda #$00
  sta PPUADDR
  ldx #$00
  lda #$3F ; color
.loop:
  sta PPUDATA
  inx
  cpx #32
  bne .loop
  rts

  ; nametable cleanup
clear_screen:
  lda #$20
  sta PPUADDR
  lda #$00
  sta PPUADDR
  lda #$00
  ldx #0
  ldy #$10
.loop:
  sta PPUDATA
  inx
  bne .loop
  dey
  bne .loop
  rts

  ; clear all sprites data
clear_sprites:
  lda #$FF
  ldx #0
.loop:
  sta SPRITES, x
  inx
  bne .loop
  rts

  ; DMA sprites loading
sprite_dma_copy:
  pha
  lda #0
  sta OAMADDR
  lda #HIGH(SPRITES)
  sta OAMDMA
  pla
  rts

  ; loading header (image on the top), first part
draw_header1:
  lda #BANK(nametable_header) / 2 ; bank with header
  jsr select_prg_bank
  ldx #0
  ldy #$40
.loop:
  lda nametable_header, x
  sta PPUDATA
  inx
  dey
  bne .loop
  rts

  ; loading header (image on the top), second part
draw_header2:
  lda #BANK(nametable_header) / 2 ; bank with header
  jsr select_prg_bank
  ldx #$40
  ldy #$40
.loop:
  lda nametable_header, x
  sta PPUDATA
  inx
  dey
  bne .loop
  rts


  ; printing game name on the top
print_first_name:
  rts

  ; printing game name on the bottom
print_last_name:
  rts

print_name:
  pha
  tya
  pha
  txa
  pha

  ; --- 1. PPU AADRESS ---
  bit $2002
  lda <TEXT_DRAW_ROW
  lsr a
  lsr a
  lsr a
  ora #$20
  sta $2006
  lda <TEXT_DRAW_ROW
  asl a
  asl a
  asl a
  asl a
  asl a
  sta $2006

  ; --- 2. SERVA OFFSET ---
  ldy #0
  lda #$00
.offset_loop:
  sta $2007
  iny
  cpy #GAME_NAMES_OFFSET
  bne .offset_loop

  ; --- 3. PANGA VALIK ---
  ; Oluline: Builder lükkab tavaliselt 256 mängu kaupa panku.
  lda #BANK(game_names) / 2
  ldx <TEXT_DRAW_GAME+1  ; Võtame mängu nr kõrge baidi (0, 1, 2...)
  stx <TMP               ; Kasutame TMP-d panga nihke jaoks
  clc
  adc <TMP
  jsr select_prg_bank

  ; --- 4. POINTERI AADRESSI ARVUTAMINE ---
  ; Aadress = game_names + (madal_bait * 2)
  lda <TEXT_DRAW_GAME
  asl a
  sta <COPY_SOURCE_ADDR
  lda #HIGH(game_names)
  adc #0                 ; Lisa carry, kui asl a läks üle (mäng 128!)
  sta <COPY_SOURCE_ADDR+1
  
  lda <COPY_SOURCE_ADDR
  clc
  adc #LOW(game_names)
  sta <COPY_SOURCE_ADDR
  lda <COPY_SOURCE_ADDR+1
  adc #0
  sta <COPY_SOURCE_ADDR+1

  ; --- 5. LAADI NIMI JA KONTROLLI PANKA ---
  ldy #0
  lda [COPY_SOURCE_ADDR], y
  tax
  iny
  lda [COPY_SOURCE_ADDR], y
  sta <COPY_SOURCE_ADDR+1
  stx <COPY_SOURCE_ADDR

  ; Kui nime aadress on >= $C000, asub tekst järgmises mälupangas
  lda <COPY_SOURCE_ADDR+1
  cmp #$C0
  bcc .no_extra_bank
  lda #BANK(game_names) / 2
  clc
  adc <TMP
  adc #1
  jsr select_prg_bank
  lda <COPY_SOURCE_ADDR+1
  sec
  sbc #$40
  sta <COPY_SOURCE_ADDR+1
.no_extra_bank:

  ; --- 6. TRÜKKIMINE ---
  ldy #0
.char_loop:
  lda [COPY_SOURCE_ADDR], y
  beq .fill_rest
  sta $2007
  iny
  cpy #28
  bne .char_loop

.fill_rest:
  lda #$00
.fill_loop:
  cpy #28
  bcs .exit
  sta $2007
  iny
  jmp .fill_loop

.exit:
  pla
  tax
  pla
  tay
  pla
  rts

print_empty_row:
  bit $2002
  lda <TEXT_DRAW_ROW
  lsr a
  lsr a
  lsr a
  ora #$20
  sta $2006
  lda <TEXT_DRAW_ROW
  asl a
  asl a
  asl a
  asl a
  asl a
  sta $2006
  ldy #32
  lda #$00          ; Tühik/tühi tile
.l:
  sta $2007
  dey
  bne .l
  rts

set_line_attributes:
  ; maybe this line already drawned?
  ; lda <TEXT_DRAW_ROW
  ; and #%11111110
  ; cmp <LAST_ATTRIBUTE_ADDRESS
  ; bne .set_attribute_address
  rts
.set_attribute_address:
  lda #BANK(header_attribute_table) / 2
  jsr select_prg_bank
  ; calculating attributes address
  lda <TEXT_DRAW_ROW
  cmp #LINES_PER_SCREEN
  bcc .first_screen
  ; second nametable
  lda #1
  sta TMP ; remember nametable #
  lda #$2F
  sta PPUADDR
  lda <TEXT_DRAW_ROW
  sec
  sbc #LINES_PER_SCREEN
  jmp .nametable_detect_end
  ; first nametable
.first_screen:
  lda #0
  sta TMP ; remember nametable #
  lda #$23
  sta PPUADDR
  lda <TEXT_DRAW_ROW
.nametable_detect_end:
  ; one byte for 4 rows
  and #%11111110
  asl A
  asl A
  clc
  adc #$C0
  sta <LAST_ATTRIBUTE_ADDRESS
  sta PPUADDR
  ; now writing attributes, need to calculate them too
  ldx #8
  ldy #0
  lda <TEXT_DRAW_GAME+1
  cmp #HIGH(GAMES_COUNT + 3)
  bne .not_footer
  lda <TEXT_DRAW_GAME
  cmp #LOW(GAMES_COUNT + 3)
  jmp .maybe_header_or_game_0
.not_footer:
  cmp #0
  bne .only_text_attributes
.maybe_header_or_game_0:
  lda <TEXT_DRAW_GAME+1
  bne .only_text_attributes
  lda <TEXT_DRAW_GAME
  cmp #0
  beq .header_0
  cmp #1
  beq .header_1
  cmp #2
  beq .game_0
  jmp .only_text_attributes
.header_0
  lda TEXT_DRAW_ROW
  eor TMP
  lsr A
  bcc .only_header_attributes
.header_0_loop:
  lda header_attribute_table, y
  asl A
  asl A
  asl A
  ora #$0F
  sta PPUDATA
  iny
  dex
  bne .header_0_loop
  rts
.header_1
  lda TEXT_DRAW_ROW
  eor TMP
  lsr A
  bcs .only_header_attributes
.header_1_loop:
  lda header_attribute_table, y
  lsr A
  lsr A
  lsr A
  clc
  ora #$F0
  sta PPUDATA
  iny
  dex
  bne .header_1_loop
  rts
.game_0:
  lda TEXT_DRAW_ROW
  eor TMP
  lsr A
  bcc .only_text_attributes
  jmp .header_1_loop
.only_header_attributes:
  lda header_attribute_table, y
  sta PPUDATA
  iny
  dex
  bne .only_header_attributes
  rts
.only_text_attributes:
    rts
move_cursors:
  pha
  ; Sunnime Y-koordinaadi kohe sihtmärgile ilma liuglemiseta
  lda <SPRITE_Y_TARGET
  sta SPRITE_0_Y
  .if ENABLE_RIGHT_CURSOR!=0
  sta SPRITE_1_Y
  .endif

  ; Sunnime ka X-koordinaadid paika
  lda <SPRITE_0_X_TARGET
  sta SPRITE_0_X
  lda <SPRITE_1_X_TARGET
  sta SPRITE_1_X
  
  pla
  rts
  ; fine scrolling to target line
move_scrolling:
  rts

set_scroll_targets:
  lda #0
  sta <SCROLL_LINES_TARGET
  sta <SCROLL_LINES_TARGET+1
  sta <SCROLL_LINES
  sta <SCROLL_LINES+1
  sta <SCROLL_LINES_MODULO
  
  jsr set_cursor_targets
  rts

set_cursor_targets:
  jsr calculate_page_pos ; Nüüd on A-registris 0-19
  sta <TMP              ; Hoiame hetke positsiooni lehel

  ; --- UUS: KONTROLL VIIMASE LEHE JAOKS ---
  ; Me ei taha, et kursor läheb ridadele, kus mänge pole
  lda <SELECTED_GAME
  cmp #LOW(GAMES_COUNT)
  lda <SELECTED_GAME+1
  sbc #HIGH(GAMES_COUNT)
  bcc .pos_ok           ; Kui SELECTED_GAME < 403, siis on kõik timm
  
  ; Kui oleme üle piiri, sunnime kursori viimasele olemasolevale mängule
  ; (Vabatahtlik: see hoiab ära kursori "hüpete" sünkroonist väljamineku)
  
.pos_ok:
  lda <TMP              ; Võtame positsiooni (0-19) uuesti
  asl a                 ; x2
  asl a                 ; x4
  asl a                 ; x8 (piksleid rea kohta)
  clc
  adc #63               ; Baas-Y-koordinaat (päise algus)
  sta <SPRITE_Y_TARGET

  ; X-koordinaat (Sama mis sul oli)
  lda #(GAME_NAMES_OFFSET * 8 - 8) 
  sta <SPRITE_0_X_TARGET
  rts

wait_scroll_done:
  ; just to make sure that screen drawing done
  jsr waitblank
  lda <SCROLL_LINES
  cmp <SCROLL_LINES_TARGET
  bne wait_scroll_done
  lda <SCROLL_LINES+1
  cmp <SCROLL_LINES_TARGET+1
  bne wait_scroll_done
  rts

  .if STARS!=0
  .if STARS < 0
  .fail STARS must be > 0
  .endif
  .if STARS > 62
  .fail STARS must be <= 62
  .endif
stars:
  ; one time spawner
  lda <STAR_SPAWN_COUNTER
  cmp #STARS ; number of stars
  beq .spawn_end ; spawner is not required anymore
  inc <STAR_SPAWN_TIMER
  lda <STAR_SPAWN_TIMER
  cmp #STAR_SPAWN_INTERVAL ; spawn interval
  bne .spawn_end ; too early
  lda #0
  sta <STAR_SPAWN_TIMER
  lda <STAR_SPAWN_COUNTER
  asl A
  asl A
  tay
  jsr .spawn
  inc <STAR_SPAWN_COUNTER
.spawn_end:
  ldy #0
.move_next:
  lda SPRITES+4*2, y
  cmp #$FF ; end of stars marker
  beq .move_end
  tya
  lsr A
  lsr A
  and #$07
  cmp #$00
  beq .move_fast
  cmp #$01
  beq .move_fast
  cmp #$02
  beq .move_fast
  cmp #$03
  beq .move_medium
  cmp #$04
  beq .move_medium
  cmp #$05
  beq .move_slow
  cmp #$06
  beq .move_slow
  .if STARS_DIRECTION=0
.move_very_slow:
  lda SPRITES+4*2, y
  sec
  sbc #1
  jmp .moved
.move_slow:
  lda SPRITES+4*2, y
  sec
  sbc #2
  jmp .moved
.move_medium:
  lda SPRITES+4*2, y
  sec
  sbc #3
  jmp .moved
.move_fast:
  lda SPRITES+4*2, y
  sec
  sbc #4
  .else
.move_very_slow:
  lda SPRITES+4*2, y
  clc
  adc #1
  jmp .moved
.move_slow:
  lda SPRITES+4*2, y
  clc
  adc #2
  jmp .moved
.move_medium:
  lda SPRITES+4*2, y
  clc
  adc #3
  jmp .moved
.move_fast:
  lda SPRITES+4*2, y
  clc
  adc #4
  .endif
.moved:
  sta SPRITES+4*2, y
  ; reset Y coordinate
  ; if sprite out of the screen
  .if STARS_DIRECTION=0
  cmp #$04
  bcs .move_next1
  .else
  cmp #$FB
  bcc .move_next1
  .endif
  jsr .spawn
.move_next1:
  iny
  iny
  iny
  iny
  bne .move_next
.move_end:
  rts
.spawn:
  ; set Y
  .if STARS_DIRECTION=0
  lda #$FE ; Y, below the screen
  .else
  lda #$00 ; Y, top of the screen
  .endif
  sta SPRITES+4*2, y
  ; set random tile
  jsr random
  and #$03
  clc
  adc #1
  sta SPRITES+4*2+1, y
  ; set random attributes
  jsr random ; attributes, random palette
  and #%00000011 ; palette - two lowest bits
  ora #%00100000 ; low priority bit
  sta SPRITES+4*2+2, y
  ; set random X
  jsr random
  sta SPRITES+4*2+3, y
  rts
  .endif

load_text_attributes:
  lda #$23
  sta PPUADDR
  lda #$C8
  sta PPUADDR
  lda #$FF
  ldy #$38
.loop:
  sta PPUDATA
  dey
  bne .loop
  rts

  ; print null-terminated string from [COPY_SOURCE_ADDR]
print_text:
  ldy #0
.loop:
  lda [COPY_SOURCE_ADDR], y
  sta PPUDATA
  iny
  cmp #0 ; stop at zero
  bne .loop
  rts

  ; show "saving... keep power on" message
saving_warning_show:
  lda <SAVE_WARNED
  beq .continue
  rts
.continue:
  inc <SAVE_WARNED
  ; disable PPU
  lda #%00000000
  sta PPUCTRL
  sta PPUMASK
  jsr waitblank_simple
  ; print text
  jsr clear_screen
  lda #$21
  sta PPUADDR
  lda #$C0
  sta PPUADDR
  lda #LOW(string_saving)
  sta COPY_SOURCE_ADDR
  lda #HIGH(string_saving)
  sta COPY_SOURCE_ADDR+1
  jsr print_text
  jsr load_text_attributes
  ; enable PPU
  lda #%00001000
  sta PPUCTRL
  lda #%00001010
  sta PPUMASK
  ; disable scrolling
  inc SCROLL_LOCK
  ; dim-in
  jsr dim_base_palette_in
  rts

  ; hide this message (clear screen)
saving_warning_hide:
  lda <SAVE_WARNED
  bne .continue
  rts
.continue:
  lda #0
  sta <SAVE_WARNED
  jsr dim_base_palette_out
  lda #%00000000 ; disable PPU
  sta PPUCTRL
  sta PPUMASK
  sta SCROLL_LOCK
  rts

detect_chr_ram_size:
  ; disable PPU
  lda #%00000000
  sta PPUCTRL
  sta PPUMASK
  jsr waitblank_simple
  jsr enable_chr_write
  lda #$00
  sta PPUADDR
  sta PPUADDR
  ; store $AA to zero bank
  sta <CHR_RAM_SIZE
  lda #$AA
  sta PPUDATA
  ; calculate bank number
.next_size:
  lda #1
  ldx CHR_RAM_SIZE
  ; shift 1 to the left CHR_RAM_SIZE times
.shift_loop:
  dex
  bmi .shift_done
  asl A
  beq .end ; overflow check
  jmp .shift_loop
.shift_done:
  ; select this bank
  jsr select_chr_bank
  ; store $AA
  ldx #$00
  stx PPUADDR
  stx PPUADDR
  lda #$AA
  sta PPUDATA
  ; to prevent open bus read
  lda #$55
  sta PPUDATA
  ; check for $AA
  stx PPUADDR
  stx PPUADDR
  ldy PPUDATA ; dump read
  lda #$AA
  cmp PPUDATA
  bne .end ; check failed
  ; store $55
  stx PPUADDR
  stx PPUADDR
  lda #$55
  sta PPUDATA
  ; to prevent open bus read
  lda #$AA
  sta PPUDATA
  ; check for $55a
  stx PPUADDR
  stx PPUADDR
  ldy PPUDATA ; dump read
  lda #$55
  cmp PPUDATA
  bne .end ; check failed
  ; select zero bank
  lda #0
  jsr select_chr_bank
  ; check that $AA is not overwrited
  stx PPUADDR
  stx PPUADDR
  lda #$AA
  ldy PPUDATA ; dump read
  cmp PPUDATA
  bne .end ; check failed
  ; OK! Let's check next bank
  inc <CHR_RAM_SIZE
  jmp .next_size
.end:
  ; return everything back
  lda #0
  jsr select_chr_bank
  jsr load_base_chr
  jsr disable_chr_write
  rts

calculate_page_pos:
  lda <SELECTED_GAME
  sta <TMP
  lda <SELECTED_GAME+1
  sta <TMP+1

  ; Kui mäng on 0, siis on kindlasti lehe algus
  ora <TMP
  beq .done

.loop:
  ; Kontrollime 16-bitiselt, kas jääk on alla 20
  lda <TMP+1
  bne .sub_20
  lda <TMP
  cmp #20
  bcc .done

.sub_20:
  lda <TMP
  sec
  sbc #20
  sta <TMP
  lda <TMP+1
  sbc #0
  sta <TMP+1
  jmp .loop

.done:
  lda <TMP    ; Tagastab 0-19
  rts

; ==============================================================================
; MÄNGUDE NIMEKIRJA JOONISTAMINE (20 mängu lehel)
; ==============================================================================

redraw_entire_page:
  ; 1. Pilt ja PPU välja, et saaksime vabalt kirjutada
  lda #%00000000
  sta PPUMASK
  sta PPUCTRL
  
  lda #0
  sta <SCROLL_LINES
  sta <SCROLL_LINES+1

  jsr waitblank_simple
  jsr clear_screen

  ; --- 2. VÄRVID / ATRIBUUDID ---
  bit $2002
  lda #$23
  sta $2006
  lda #$C0
  sta $2006

  ; Päise värv (Palette 0)
  lda #$00
  ldx #$10
.attr_h_loop:
  sta $2007
  dex
  bne .attr_h_loop

  ; Nimekirja värv (Palette 2 - Hall tekst)
  lda #$FF
  ldx #$30
.attr_l_loop:
  sta $2007
  dex
  bne .attr_l_loop

  ; --- 3. GRAAFILINE PÄIS ---
  bit $2002
  lda #$20
  sta $2006
  lda #$40        
  sta $2006
  jsr draw_header1
  jsr draw_header2

  ; --- 4. LEHE ALGUSE ARVUTAMINE (16-bitine loogika) ---
  ; Algatame TEXT_DRAW_GAME nullist
  lda #0
  sta <TEXT_DRAW_GAME
  sta <TEXT_DRAW_GAME+1

  ; Teeme SELECTED_GAME-ist koopia TMP-sse, mida saame vähendada
  lda <SELECTED_GAME
  sta <TMP
  lda <SELECTED_GAME+1
  sta <TMP+1

.find_page_loop:
  ; KONTROLL: Kas TMP:TMP+1 < 20?
  lda <TMP+1
  bne .sub_20          ; Kui kõrge bait > 0, on arv kindlasti >= 20
  lda <TMP
  cmp #20
  bcc .found_start     ; Kui on < 20, oleme lehe alguse leidnud

.sub_20:
  ; TMP = TMP - 20 (16-bit)
  lda <TMP
  sec
  sbc #20
  sta <TMP
  lda <TMP+1
  sbc #0
  sta <TMP+1

  ; TEXT_DRAW_GAME = TEXT_DRAW_GAME + 20 (16-bit)
  lda <TEXT_DRAW_GAME
  clc
  adc #20
  sta <TEXT_DRAW_GAME
  lda <TEXT_DRAW_GAME+1
  adc #0
  sta <TEXT_DRAW_GAME+1
  
  jmp .find_page_loop

.found_start:
  ; Nüüd on TEXT_DRAW_GAME paigas (0, 20, 40 ... 240, 260 jne)
  lda #8                ; Nimekirja esimene rida ekraanil
  sta <TEXT_DRAW_ROW
  ldx #20               ; Joonistame 20 rida
             
.draw_loop:
  stx <TMP+1            ; Kasutame TMP+1 ridade loendurina
  
  ; --- KONTROLL: Kas praegune mäng on nimekirja piires? ---
  lda <TEXT_DRAW_GAME
  cmp #LOW(GAMES_COUNT)
  lda <TEXT_DRAW_GAME+1
  sbc #HIGH(GAMES_COUNT)
  bcs .draw_empty_line  ; Kui DRAW_GAME >= GAMES_COUNT, joonista tühi rida

  jsr print_name        ; See rutiin peab kasutama TEXT_DRAW_GAME väärtust
  jmp .next_line

.draw_empty_line:
  jsr print_empty_row

.next_line:
  ; TEXT_DRAW_GAME++ (16-bitine suurendamine)
  inc <TEXT_DRAW_GAME
  bne .no_inc
  inc <TEXT_DRAW_GAME+1
.no_inc:

  inc <TEXT_DRAW_ROW
  ldx <TMP+1
  dex
  bne .draw_loop

  ; --- 5. PILT TAGASI ETTE ---
  jsr waitblank_simple
  bit $2002
  lda #0
  sta $2005
  sta $2005
  lda #%10001000
  sta PPUCTRL
  lda #%00011110
  sta PPUMASK
  
  ; Uuendame kursori asukohta vastavalt uuele lehele
  jsr move_cursors
  rts

set_ppu_for_row:
  pha
  txa
  pha
  lda <TEXT_DRAW_ROW    ; Võtame rea numbri (nt 6)
  ldx #0
  stx <TMP              ; Puhastame ajutise muutuja
  
  ; Arvutus: Aadress = $2000 + (Rida * 32)
  asl a                 ; x2
  asl a                 ; x4
  asl a                 ; x8
  asl a                 ; x16
  asl a                 ; x32
  rol <TMP              ; Kui läheb üle 255, siis TMP-sse (kõrge bait)
  
  sta $2006             ; Madal bait
  lda <TMP
  ora #$20              ; Nametable $2000 algus
  sta $2006             ; Kõrge bait
  pla
  tax
  pla
  rts
