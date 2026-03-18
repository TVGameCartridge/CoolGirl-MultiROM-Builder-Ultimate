BUTTONS .rs 1 ; currently pressed buttons
BUTTONS_TMP .rs 1 ; temporary variable for buttons
BUTTONS_HOLD_TIME .rs 1 ; up/down/left/right buttons hold time
KONAMI_CODE_STATE .rs 1 ; Konami Code state

  .if GAMES_COUNT >= 20
MAXIMUM_SCROLL .equ GAMES_COUNT - 20
  .else
MAXIMUM_SCROLL .equ 20
  .endif

  ; controller reading, two times
read_controller:
  pha
  tya
  pha
  txa
  pha
  jsr .real ; first read
  ldx <BUTTONS_TMP
  jsr .real ; second read
  cpx <BUTTONS_TMP ; lets compare values
  bne .end ; ignore it if not equal
  stx <BUTTONS ; storing value
  txa
  and #%11110000 ; up/down/left/right
  beq .no_up_down ; is pressed?
  inc <BUTTONS_HOLD_TIME ; increasing hold time
  lda <BUTTONS_HOLD_TIME
  cmp #BUTTON_REPEAT_FRAMES ; is it holding long enought?
  bcc .end ; no
  lda #0 ; yes, it's long enought, so lets "release" buttons
  sta <BUTTONS
  lda #BUTTON_REPEAT_FRAMES - 10 ; autorepeat time = 10
  sta <BUTTONS_HOLD_TIME
  jmp .end
.no_up_down:
  lda #0 ; reset hold time
  sta <BUTTONS_HOLD_TIME
.end:
  pla
  tax
  pla
  tay
  pla
  rts

  ; real controller read, stores buttons to BUTTONS_TMP
.real:
  lda #1
  sta JOY1
  lda #0
  sta JOY1
  ldy #8
.read_button:
  lda JOY1
  and #$03
  cmp #$01
  ror <BUTTONS_TMP
  dey
  bne .read_button
  rts

  ; check buttons state and do some action
buttons_check:
  ; if buttons are not pressed at all return immediately
  lda <BUTTONS
  cmp #$00
  bne .start_check
  rts
.start_check:
  jsr konami_code_check
.button_a:
  lda <BUTTONS
  and #%00000001
  beq .button_b
  jmp start_game

.button_b:
  lda <BUTTONS
  and #%00000010
  beq .button_start
  ; nothing to do
  jmp .button_end

.button_start:
  lda <BUTTONS
  and #%00001000
  beq .button_up
  jmp start_game

.button_up:
  lda <BUTTONS
  and #%00010000        ; Üles nupp
  beq .skip_up_jump     ; Kui Üles ei vajutatud, hüppa üle
  jmp .do_button_up     ; Kui vajutati, mine päris loogika juurde
.skip_up_jump:
  jmp .button_down      ; Edasi alla nupu kontrolli juurde

.do_button_up:
  lda <SELECTED_GAME
  ora <SELECTED_GAME+1  ; Kontrollime, kas mõlemad baidid on 0
  beq .jump_to_last     ; Kui on 0, siis hüppa nimekirja lõppu

  .if ENABLE_SOUND!=0
  jsr bleep
  .endif

  ; Kontrolli, kas oleme lehe ülaservas
  jsr check_if_page_top 
  beq .jump_prev_page   ; Kui jah, siis lehe vahetus
  
  ; Tavaline liikumine üles (16-bit lahutamine)
  lda <SELECTED_GAME
  sec
  sbc #1
  sta <SELECTED_GAME
  lda <SELECTED_GAME+1
  sbc #0
  sta <SELECTED_GAME+1
  jmp .button_end

.jump_to_last:

  ; LISATUD HELI HÜPPE AJAKS
  .if ENABLE_SOUND!=0
  jsr bleep             ; Nüüd teeb piiksu ka siin!
  .endif

  ; Hüpe esimeselt mängult viimasele
  lda #LOW(GAMES_COUNT-1)
  sta <SELECTED_GAME
  lda #HIGH(GAMES_COUNT-1)
  sta <SELECTED_GAME+1
  jsr redraw_entire_page ; Kuna liigume esimeselt lehelt viimasele
  jmp .button_end

.jump_prev_page:
  lda <SELECTED_GAME
  sec
  sbc #1
  sta <SELECTED_GAME
  lda <SELECTED_GAME+1
  sbc #0
  sta <SELECTED_GAME+1
  jsr redraw_entire_page 
  jmp .button_end

.button_down:
  lda <BUTTONS
  and #%00100000        ; Kas vajutati ALLA?
  beq .button_left
  
  ; Kontrollime, kas oleme päris viimase mängu juures (GAMES_COUNT-1)
  lda <SELECTED_GAME
  clc
  adc #1
  tax
  lda <SELECTED_GAME+1
  adc #0
  tay
  
  ; 16-bit võrdlus GAMES_COUNT-ga
  cpy #HIGH(GAMES_COUNT)
  bne .down_not_end
  cpx #LOW(GAMES_COUNT)
  bcc .down_not_end

; KUI JÕUDSIME LÕPPU -> Hüppa algusesse
  .if ENABLE_SOUND!=0
  jsr bleep             ; Piiks ka siia!
  .endif

  lda #0
  sta <SELECTED_GAME
  sta <SELECTED_GAME+1
  jsr redraw_entire_page
  jmp .button_end

.down_not_end:
  stx <SELECTED_GAME    
  sty <SELECTED_GAME+1

  .if ENABLE_SOUND!=0
  jsr bleep             
  .endif

  ; KONTROLL: Kas uue mängu positsioon lehel on 0?
  jsr check_if_page_top
  bne .button_end       
  jsr redraw_entire_page 
  jmp .button_end

.button_left:
  lda <BUTTONS
  and #%01000000        ; Vasakule nupp
  beq .button_right
  
  ; Kontrollime, kas oleme esimesel lehel (0-19)
  lda <SELECTED_GAME+1
  bne .left_ok          ; Kui kõrge bait pole 0, võib julgelt lahutada
  lda <SELECTED_GAME
  cmp #20
  bcc .wrap_to_end      ; Kui on 0-19, siis hüppa lõppu!

.left_ok:
  lda <SELECTED_GAME
  sec
  sbc #20
  sta <SELECTED_GAME
  lda <SELECTED_GAME+1
  sbc #0
  sta <SELECTED_GAME+1
  jmp .left_redraw

.wrap_to_end:
  lda #LOW(GAMES_COUNT-1)
  sta <SELECTED_GAME
  lda #HIGH(GAMES_COUNT-1)
  sta <SELECTED_GAME+1

.left_redraw:
  .if ENABLE_SOUND!=0
  jsr start_sound
  .endif
  jsr redraw_entire_page
  jmp .button_end

.button_right:
  lda <BUTTONS
  and #%10000000        ; Paremale nupp
  beq .button_end
  
  ; 1. Arvutame potentsiaalse uue asukoha (+20)
  lda <SELECTED_GAME
  clc
  adc #20
  tax
  lda <SELECTED_GAME+1
  adc #0
  tay
  
  ; 2. KONTROLL: Kas see asukoht on veel nimekirja piires?
  cpy #HIGH(GAMES_COUNT)
  bne .check_wrap_right
  cpx #LOW(GAMES_COUNT)

.check_wrap_right:
  bcc .do_right_move     ; Kui on väiksem kui GAMES_COUNT, siis tee tavaline hüpe
  
  ; 3. Kui läks üle piiri, siis HÜPPA ALGUSESSE (Ring täis)
  lda #0
  sta <SELECTED_GAME
  sta <SELECTED_GAME+1
  jmp .right_redraw_forced

.do_right_move:
  ; Kui oli piires, salvestame arvutatud X ja Y
  stx <SELECTED_GAME
  sty <SELECTED_GAME+1

.right_redraw_forced:
  .if ENABLE_SOUND!=0
  jsr start_sound
  .endif
  jsr redraw_entire_page
  jmp .button_end
.button_none:
  ; this code shouldn't never ever be executed
  rts

.button_end:
  jsr set_scroll_targets ; updating cursor targets
  ; saving last cursor position
  .if (INSTANT_STATE_SAVE!=0) & (ENABLE_LAST_GAME_SAVING!=0)
  jsr save_state
  .endif
  ; waiting until buttons released
  jsr wait_buttons_not_pressed
  rts

; need to skip separator when scrolling upwards
check_separator_down:
  lda <SELECTED_GAME+1
  jsr select_prg_bank
  ldx <SELECTED_GAME
  lda loader_data_game_flags, x
  and #$80
  beq check_separator_down_end
  lda <SELECTED_GAME
  clc
  adc #1
  sta <SELECTED_GAME
  lda <SELECTED_GAME+1
  adc #0
  sta <SELECTED_GAME+1
  cmp #HIGH(GAMES_COUNT)
  bne check_separator_down
  lda <SELECTED_GAME
  cmp #LOW(GAMES_COUNT)
  bne check_separator_down
  .if GAMES_COUNT < WRAP_GAMES
  lda #0
  sta <SELECTED_GAME
  sta <SELECTED_GAME+1
  sta <SCROLL_LINES_TARGET
  sta <SCROLL_LINES_TARGET+1
  .else
  jsr screen_wrap_down
  .endif
  jmp check_separator_down
check_separator_down_end:
  rts

; need to skip separator when scrolling downwards
check_separator_up:
  lda <SELECTED_GAME+1
  jsr select_prg_bank
  ldx <SELECTED_GAME
  lda loader_data_game_flags, x
  and #$80
  beq check_separator_up_end
  lda <SELECTED_GAME
  sec
  sbc #1
  sta <SELECTED_GAME
  lda <SELECTED_GAME+1
  sbc #0
  sta <SELECTED_GAME+1
  bpl check_separator_up
  .if GAMES_COUNT < WRAP_GAMES
  lda #LOW(GAMES_COUNT - 1)
  sta <SELECTED_GAME
  lda #HIGH(GAMES_COUNT - 1)
  sta <SELECTED_GAME+1
  .else
  jsr screen_wrap_up
  .endif
  jmp check_separator_up
check_separator_up_end:
  rts

  ; waiting for button release
wait_buttons_not_pressed:
  jsr waitblank ; waiting for v-blank
  lda <BUTTONS
  bne wait_buttons_not_pressed
  rts

  ; waiting for button release, really
wait_buttons_really_not_pressed:
  jsr waitblank ; waiting for v-blank
  lda <BUTTONS
  bne wait_buttons_really_not_pressed
  lda BUTTONS_HOLD_TIME
  bne wait_buttons_really_not_pressed
  rts

konami_code_check:
  ldy <KONAMI_CODE_STATE
  lda konami_code, y
  cmp <BUTTONS
  bne konami_code_check_fail
  iny
  jmp konami_code_check_end
konami_code_check_fail:
  ldy #0
  lda konami_code ; in case when newpressed button is first button of code
  cmp <BUTTONS
  bne konami_code_check_end
  iny
konami_code_check_end:
  sty <KONAMI_CODE_STATE
  rts

konami_code:
  .db $10, $10, $20, $20, $40, $80, $40, $80, $02, $01
konami_code_length:
  .db 10

check_if_page_top:
  lda <SELECTED_GAME
  sta <TMP
  lda <SELECTED_GAME+1
  sta <TMP+1
.loop:
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
  lda <TMP    ; A on nüüd 0-19. Kui A=0, on lehe algus.
  cmp #0
  rts

check_if_page_bottom:
  lda <SELECTED_GAME
.mod_loop:
  cmp #20
  bcc .done
  sec
  sbc #20
  jmp .mod_loop
.done:
  cmp #25
  ; Kui tulemus on 19, siis Z-lipp on püsti ja BEQ toimib
  rts
