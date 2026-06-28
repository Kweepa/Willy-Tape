; Rope animation test harness — 24x20 VIC-20 environment for rope_draw.asm

!set ROPE_TEST = 0

; rope_draw.asm ZP and layout (subset of zp.asm / defines.asm / header.asm)
guardian_sprites_base = $1a58
GUARDIAN_CHR = 22
TILE_CHR_BASE = 16
ROPE_ANCHOR_COL = 12
ROPE_ANCHOR_PY = 8
ROPE_FIRST_UDG = GUARDIAN_CHR + 12
ROPE_UDG_BYTES = 128
ROPE_XADD_BYTES = 54
ROPE_SEGMENT_Y = $33c
ROPE_XADD = $35c
rope_xadd = ROPE_XADD

rope_old_screen_pos = $68
rope_udg            = $88
rope_frame          = $89
rope_swing_side     = $8a
rope_swing_dir      = $8b
rope_scr            = $8c
rope_bit            = $8e
rope_y              = $8f
rope_udg_mem        = $96
rope_index          = $98
rope_udg_advance    = $99
rope_willy_is_holding = $9a
rope_willy_seg      = $9b
rope_segment_cur_x  = $9c
rope_segment_cur_y  = $9d
rope_seg_skip_above = $9e
rope_loop_count     = $9f
rope_grab_cooldown  = $67

on_ground       = $18
px              = $10
py              = $11
scr_ptr         = $05
print_tmp       = $04
ts              = $50
debug_x_step    = $02
debug_y_step    = $03

; VIC layout (subset of defines.asm / header.asm)
udg_base        = $1c00
EMPTY_CHR       = 16
GREEN           = 5
BLUE            = 6
screen_base     = $1e00
ROPE_ANCHOR_SCR = screen_base + ROPE_ANCHOR_COL
ROPE_FIRST_UDG_ADDRESS = udg_base + ROPE_FIRST_UDG * 8
color_base      = $9600
basic_start     = $1000

; mkroom.py ascii_to_rom_screen: A-Z + $40, 0-9 + $80 ($b0 base for digit 0)
SCREEN_LETTER_OFF = $40
SCREEN_DIGIT_OFF  = $80
SCREEN_DIGIT_BASE = $b0

test_rows       = 20
test_cols       = 24
test_tile_bytes = test_rows * test_cols
debug_row0      = screen_base + 17 * test_cols
debug_row1      = screen_base + 18 * test_cols
debug_row2      = screen_base + 19 * test_cols

RASTERLINE_PAL  = $6e

; BASIC SYS 4109 -> WarmStart
*=basic_start-1
    !word basic_start+1
    !word basic_end
    !word 10
    !byte $9e
    !text "4109"
    !byte 0
basic_end
    !word 0

cold_start
warm_start
    jmp WarmStart

start_game
    jsr InitScreen
    jsr InitRope
    sei
    jsr rope_draw
rope_loop
    jsr rope_clear_pre_player_draw
    lda #(BLUE + 8)
    sta $900f
    jsr rope_draw
    lda #(GREEN + 8)
    sta $900f
    jsr WaitForRaster
    jmp rope_loop

rope_test_loop_hook
    jsr DrawDebugHud
    ; jsr WaitForSpaceStep
    rts

WaitForRasterLine
    lda $9004
    and #$fe
    cmp #RASTERLINE_PAL
    bne WaitForRasterLine
    rts

WaitForRasterLineLessThan
    lda $9004
    and #$fe
    cmp #RASTERLINE_PAL
    bcs WaitForRasterLineLessThan
    rts

WaitForRaster
    jsr WaitForRasterLineLessThan
    jmp WaitForRasterLine

; VIC keyboard matrix scan — same as input.asm (step mode; unused while animating)
ScanKeyRow
    lda #$ff
    sta $9122
    lda #$00
    sta $9123
    stx $9120
    sty ts
    lda $9121
    eor #$ff
    and ts
    tax
    rts

; Block until space pressed then released (step mode; unused while animating)
WaitForSpaceStep
-
    ldx #$ef
    jsr ScanKeyRow
    beq -
-
    ldx #$ef
    jsr ScanKeyRow
    bne -
    rts

; 24x20 centred, UDG at $1C00 (same as warm.asm but 20 rows, recentred)
WarmStart
    sei

    lda #$7f
    sta $911d
    sta $911e

    cld
    ldx #$ff
    txs

    jsr $fdf9

    ldx #5
-
    lda init20_val,x
    sta $9000,x
    dex
    bpl -

    ldx #boot_rope_xadd_size - 1
-
    lda boot_rope_xadd_pack,x
    sta ROPE_XADD,x
    dex
    bpl -

    sei
    jmp start_game

; VIC init for 24x20 (stores init20_val[5..0] -> $9000..$9005); see warm.asm init24_val for 24x17
init20_val
    !byte $0a   ; $9000  horizontal centre (same as warm.asm)
    !byte $32   ; $9001  vertical centre ($32 in warm = 17 rows; lower = shift playfield down)
    !byte $98   ; $9002  24 columns + bit7 (screen $1E00, color $9600)
    !byte 17<<1 ; $9003  17 rows: doubled count in bits 1-6 ($22 = 17 rows in warm.asm)
    !byte $00   ; $9004  raster line read (WaitForRaster); write sets light-pen Y
    !byte $ff   ; $9005  screen block $1E00, charset/UDG block $1C00

debug_frame_scr  = debug_row0 + 3
debug_loop_scr   = debug_row0 + 8
debug_y_step_scr = debug_row0 + 14
debug_x_step_scr = debug_row0 + 21
debug_cx_scr     = debug_row1 + 3
debug_cy_scr     = debug_row2 + 3

; A = 0..99 -> two screen-code digits at (scr_ptr); preserves A, X and Y
PrintDec2
    sta print_tmp
    txa
    pha
    tya
    pha
    lda print_tmp
    ldy #SCREEN_DIGIT_BASE
-
    cmp #10
    bcc +
    sbc #10
    iny
    bne -
+
    pha
    tya
    ldy #0
    sta (scr_ptr),y
    pla
    clc
    adc #SCREEN_DIGIT_BASE
    ldy #1
    sta (scr_ptr),y
    pla
    tay
    pla
    tax
    lda print_tmp
    rts

; A = 0..255 -> three screen-code digits at (scr_ptr); preserves A, X and Y
PrintDec3
    sta print_tmp
    txa
    pha
    tya
    pha
    lda print_tmp
    ldx #SCREEN_DIGIT_BASE
-
    cmp #100
    bcc +
    sbc #100
    inx
    bcs -
+
    ldy #SCREEN_DIGIT_BASE
-
    cmp #10
    bcc ++
    sbc #10
    iny
    bne -
++
    pha
    tya
    pha
    txa
    ldy #0
    sta (scr_ptr),y
    pla
    ldy #1
    sta (scr_ptr),y
    pla
    clc
    adc #SCREEN_DIGIT_BASE
    ldy #2
    sta (scr_ptr),y
    pla
    tay
    pla
    tax
    lda print_tmp
    rts

; Value in A; .scr = absolute screen address for digits
!macro PrintDec2At .scr {
!if ROPE_TEST {
    pha
    lda #<.scr
    sta scr_ptr
    lda #>.scr
    sta scr_ptr+1
    pla
    pha
    jsr PrintDec2
    pla
}
}

!macro PrintDec3At .scr {
!if ROPE_TEST {
    pha
    lda #<.scr
    sta scr_ptr
    lda #>.scr
    sta scr_ptr+1
    pla
    pha
    jsr PrintDec3
    pla
}
}

!source "rope_draw.asm"

InitScreen
    ; clear the empty char UDG
    lda #0
    ldy #7
-
    sta udg_base + EMPTY_CHR*8,y
    dey
    bpl -

    ; write empty char to the screen
    lda #EMPTY_CHR
    ldy #0
-
    sta screen_base,y
    sta screen_base+256,y
    iny
    bne -


    lda #1
    ldy #0
-
    sta color_base,y
    sta color_base+256,y
    iny
    bne -

    lda #(GREEN + 8)
    sta $900f
!if ROPE_TEST {
    jsr InitDebugLabels
}
    rts

; Row 17: FR vv  LC vv  YS vvv  XS vvv  (all values from DrawDebugHud)
InitDebugLabels
    lda #'F' + SCREEN_LETTER_OFF
    sta debug_row0+0
    lda #'R' + SCREEN_LETTER_OFF
    sta debug_row0+1
    lda #'L' + SCREEN_LETTER_OFF
    sta debug_row0+6
    lda #'C' + SCREEN_LETTER_OFF
    sta debug_row0+7
    lda #'Y' + SCREEN_LETTER_OFF
    sta debug_row0+11
    lda #'S' + SCREEN_LETTER_OFF
    sta debug_row0+12
    lda #'X' + SCREEN_LETTER_OFF
    sta debug_row0+18
    lda #'S' + SCREEN_LETTER_OFF
    sta debug_row0+19
    lda #'C' + SCREEN_LETTER_OFF
    sta debug_row1+0
    lda #'X' + SCREEN_LETTER_OFF
    sta debug_row1+1
    lda #'C' + SCREEN_LETTER_OFF
    sta debug_row2+0
    lda #'Y' + SCREEN_LETTER_OFF
    sta debug_row2+1
    rts

InitRope
    lda #0
    sta rope_frame
    sta rope_swing_side
    sta rope_willy_is_holding
    sta on_ground
    sta px
    sta py
    sta debug_x_step
    sta debug_y_step
    lda #1
    sta rope_swing_dir
    rts

DrawDebugHud
    lda rope_frame
    +PrintDec2At debug_frame_scr

    lda rope_loop_count
    +PrintDec2At debug_loop_scr

    lda debug_y_step
    +PrintDec3At debug_y_step_scr

    lda debug_x_step
    +PrintDec3At debug_x_step_scr

    lda rope_segment_cur_x
    +PrintDec3At debug_cx_scr

    lda rope_segment_cur_y
    +PrintDec3At debug_cy_scr
    rts

!source "rope_xadd_boot.asm"
