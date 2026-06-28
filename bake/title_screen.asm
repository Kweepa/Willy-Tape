; Title screen loop + scrolling HUD message — baked into r62 @ image_base.
; CLI: -DORG=$1A05 -DSCANKEYROW=… -DWAITFORRASTER=… -DSETCOLORS=… -DLOADROOMFILE=…
;      -DHUD_SCR=… -DHUD_COL=… -DMSG_LEN=… -DHOLD_FRAMES=150 -DSCROLL_FRAMES=6
;      -DSLOT_BYTES=510 -DTITLE_BAR_COUNT=28
; Must assemble at ORG (load address); internal labels are absolute, not PC-relative.
; title_* scratch in game ZP; Moonlight tune tables below (28 bars)

!source "equates.asm"

music_bar = $43
music_delay = $44

*= ORG

TitleScreen
    lda #RED
    jsr SETCOLORS
    lda #0
    sta title_scroll_off
    sta title_phase
    sta music_bar
    sta music_delay
    sta title_music_step
    lda #HOLD_FRAMES
    sta title_hold_ctr
    lda #SCROLL_FRAMES
    sta title_scroll_ctr

.title_loop
    jsr .draw_hud
    ldx #$ef                    ; space bar row
    jsr SCANKEYROW
    bne .title_exit_keyboard
    jsr .stick_fire_pressed
    bne .title_exit_fire
    jsr .play_music
    inc music_delay
    lda music_delay
    and #$0f
    sta music_delay
    bne +
    inc title_music_step
    lda title_music_step
    cmp #3
    bcc +
    lda #0
    sta title_music_step
    inc music_bar
    lda music_bar
    cmp #TITLE_BAR_COUNT
    bcc +
    lda #0
    sta music_bar
+
    jsr WAITFORRASTER
    lda title_phase
    bne .title_scroll_tick
    dec title_hold_ctr
    bne .title_loop
    lda #1
    sta title_phase
    bne .title_loop

.title_scroll_tick
    dec title_scroll_ctr
    bne .title_loop
    lda #SCROLL_FRAMES
    sta title_scroll_ctr
    inc title_scroll_off
    lda title_scroll_off
    cmp #MSG_LEN
    bne .title_loop
    lda #0
    sta title_scroll_off
    sta title_phase
    lda #HOLD_FRAMES
    sta title_hold_ctr
    jmp .title_loop

.title_exit_keyboard
    lda #0
    sta $900a
    sta $900b
    ldx #$ef
    jsr SCANKEYROW
    bne .title_exit_keyboard     ; wait for release
    rts

.title_exit_fire
    lda #0
    sta $900a
    sta $900b
    lda #'J'
    sta room_name+1
    lda #'Y'
    sta room_name+2
    jmp LOADROOMFILE

; Z set = no fire, Z clear = fire pressed (bit 5 of $9111 active-low)
; don't need to set the DDR for joystick FIRE read. was cargo cult programming.
; will be correct on boot, and can interfere with drive ops.
.stick_fire_pressed
    lda $9111
    and #$20
    eor #$20
    rts

.play_music
    ldy music_bar
    lda title_bar_seq,y
    sta title_mpack
    lda title_mpack
    and #7
    tay
    lda title_music_step
    clc
    adc title_rh_ofs,y
    tay
    lda title_lh_triplets,y
    sta $900a
    lda title_mpack
    lsr
    lsr
    lsr
    tay
    lda title_music_step
    clc
    adc title_rh_ofs,y
    tay
    lda title_rh_triplets,y
    sta $900b
    rts

.draw_hud
    ldx #0
    ldy title_scroll_off
-
    lda scroll_msg,y
    sta HUD_SCR,x
    lda #YELLOW
    sta HUD_COL,x
    iny
    cpy #MSG_LEN
    bcc +
    ldy #0
+
    inx
    cpx #24
    bne -
    rts

scroll_msg
!source ".tmp/title_msg.inc"

; Moonlight dual: LH->$900a RH->$900b, 6+9 unique triplets, 28-bar seq.
title_bar_seq
    !byte (0<<3)+0      ; B01 m1
    !byte (0<<3)+0      ; B02 m1
    !byte (0<<3)+0      ; B03 m1
    !byte (0<<3)+0      ; B04 m1
    !byte (0<<3)+1      ; B05 m2
    !byte (0<<3)+1      ; B06 m2
    !byte (0<<3)+1      ; B07 m2
    !byte (0<<3)+1      ; B08 m2
    !byte (1<<3)+2      ; B09 m3
    !byte (1<<3)+2      ; B10 m3
    !byte (2<<3)+3      ; B11 m3
    !byte (2<<3)+3      ; B12 m3
    !byte (3<<3)+4      ; B13 m4
    !byte (0<<3)+4      ; B14 m4
    !byte (4<<3)+4      ; B15 m4
    !byte (5<<3)+4      ; B16 m4
    !byte (6<<3)+0      ; B17 m5
    !byte (0<<3)+0      ; B18 m5
    !byte (0<<3)+0      ; B19 m5
    !byte (0<<3)+4      ; B20 m5
    !byte (7<<3)+5      ; B21 m6
    !byte (7<<3)+4      ; B22 m6
    !byte (7<<3)+5      ; B23 m6
    !byte (7<<3)+4      ; B24 m6
    !byte (0<<3)+0      ; B25 m7
    !byte (0<<3)+0      ; B26 m7
    !byte (8<<3)+3      ; B27 m7
    !byte (8<<3)+3      ; B28 m7

title_lh_triplets
    !byte 199,227,227       ; LH0 C#4-C#5-C#5
    !byte 223,239,239       ; LH1 B4-B5-B5
    !byte 219,237,237       ; LH2 A4-A5-A5
    !byte 212,233,233       ; LH3 F#4-F#5-F#5
    !byte 217,236,236       ; LH4 G#4-G#5-G#5
    !byte 195,225,225       ; LH5 C4-C5-C5

title_rh_triplets
    !byte 217,227,231      ; RH0 G#4-C#5-E5
    !byte 219,227,231      ; RH1 A4-C#5-E5
    !byte 219,228,233      ; RH2 A4-D5-F#5
    !byte 217,195,212      ; RH3 G#4-C4-F#4
    !byte 217,227,229      ; RH4 G#4-C#5-D#5
    !byte 217,225,229      ; RH5 G#4-C5-D#5
    !byte 207,217,227      ; RH6 E4-G#4-C#5
    !byte 217,229,233      ; RH7 G#4-D#5-F#5
    !byte 219,227,233      ; RH8 A4-C#5-F#5

title_rh_ofs
    !byte 0,3,6,9,12,15,18,21,24

!if * > ORG + SLOT_BYTES {
    !error "TitleScreen size ", *, " exceeds ", ORG + SLOT_BYTES
}
!if * < ORG + SLOT_BYTES {
    !fill ORG + SLOT_BYTES - *, $ea
}
