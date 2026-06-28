; LoadRoom RAM canary harness — verify KERNAL LOAD does not clobber "free" $0000-$03FF.
; Loads TST.PRG (512 bytes @ $1C00-$1DFF): SETNAM / SETLFS / LOAD, CLOSE LFN 15,
; then SEI. No CLOSE before LOAD.
; Two passes: both use canary $AA (same pattern). Logs both passes;
; KERNAL after verify (restore editor ZP snapshot before KERNAL print — canary prefill
; clobbers editor ZP for print; canaries skip KERNAL OPEN/CLOSE/IEC workspace (see below).

editor_len_94 = $04             ; $0094-$0097 (saved for print, not canaried)
editor_len_io = $03             ; $0098-$009A open count / in / out device
editor_len_9b = $13             ; $009B-$00AD
editor_len_c5 = $30
editor_len_259 = $46            ; $0259-$029E (saved for print; $259-$276 not canaried)
editor_off_io = editor_len_94
editor_off_9b = editor_off_io + editor_len_io
editor_off_c5 = editor_off_9b + editor_len_9b
editor_off_259 = editor_off_c5 + editor_len_c5
editor_zp_len = editor_off_259 + editor_len_259

; Harness state lives in program RAM (harness_vars), not ZP.
; fail_log entries are 2 bytes: offset in range (X), region index (Y = 0..9).
; fail_count is the next free byte offset into fail_log (0, 2, 4, …), not entry count.
; PrintPassHeader shows entry count (fail_count / 2).

test_lfn = 15
test_device = 8
test_sa = 1
load_dest = $1c00

ind_ptr = $f5                   ; 6502 indirect only; not in canary list

GREEN = 5
RED   = 2
PURPLE = 4
YELLOW = 7
BLUE = 3
WHITE = 1

screen_rows = 23
max_fail_entries = 2 * screen_rows
max_fail_log_bytes = max_fail_entries * 2
basic_start = $1000

fail_load_mark = $ff

*=basic_start - 1
    !word basic_start + 1
    !word basic_end
    !word 10
    !byte $9e
    !text "4109"
    !byte 0
basic_end
    !word 0

cold_start
warm_start
    jmp TestMain

; Canary ranges (each filled / verified with an explicit loop):
;   0 $0002 $8E | 1 $009B $13 | 2 $00B0 $07 | 3 $00C5 $30 | 4 $00F7 $09
;   5 $0100 $C0 | 6 $0200 $59 | 7 $0277 $28 | 8 $02A1 $5F | 9 $033C $C0
; Not canaried (OPEN/CLOSE/LOAD/IEC): $0094-$009A, $0259-$0276
; Not canaried (LOAD per zp.asm): $0090-$0093, $00AE-$00AF, $00B7-$00C4
; Region 3 ($C5-$F4) is canaried but expected to fail — volatile (see zp.asm).
region_bases
    !word $0002, $009b, $00b0, $00c5, $00f7
    !word $0100, $0200, $0277, $02a1, $033c

test_name
    !text "TST"

msg_pass1
    !text "PASS1 $AA", 0
msg_pass2
    !text "PASS2 $AA", 0
msg_ok
    !text "CANARY OK", 0
msg_load
    !text "LOAD ERR", 0
msg_fail
    !text "FAIL:", 0
msg_p1
    !text "P1:", 0
msg_p2
    !text " P2:", 0

fail_log
    !fill max_fail_log_bytes, 0

editor_zp_save
    !fill editor_zp_len, 0

harness_vars
test_pattern      !byte 0
fail_count        !byte 0
hex_temp          !byte 0
scr_ptr_lo        !byte 0
scr_ptr_hi        !byte 0
fail_range        !byte 0
fail_offset       !byte 0
log_x_offset      !byte 0
log_y_table       !byte 0
pass1_fail_count  !byte 0
pass2_fail_count  !byte 0
print_pass_idx    !byte 0

pass1_fail_log
    !fill max_fail_log_bytes, 0
pass2_fail_log
    !fill max_fail_log_bytes, 0

TestMain
    sei
    lda #$7f
    sta $911d
    sta $911e

    jsr InstallStopNoop
    jsr SaveEditorZp

    lda #(YELLOW + 24)
    sta $900f
    lda #$aa
    jsr RunOnePass
    jsr SavePass1FailLog

    lda #(BLUE + 24)
    sta $900f
    lda #$aa
    jsr RunOnePass
    jsr SavePass2FailLog

    jsr PrintAllResults
    jmp PassHalt

SavePass1FailLog
    lda fail_count
    sta pass1_fail_count
    ldx #max_fail_log_bytes
    dex
-
    lda fail_log,x
    sta pass1_fail_log,x
    dex
    bpl -
    rts

SavePass2FailLog
    lda fail_count
    sta pass2_fail_count
    ldx #max_fail_log_bytes
    dex
-
    lda fail_log,x
    sta pass2_fail_log,x
    dex
    bpl -
    rts

RestorePass1FailLog
    lda pass1_fail_count
    sta fail_count
    ldx #max_fail_log_bytes
    dex
-
    lda pass1_fail_log,x
    sta fail_log,x
    dex
    bpl -
    rts

RestorePass2FailLog
    lda pass2_fail_count
    sta fail_count
    ldx #max_fail_log_bytes
    dex
-
    lda pass2_fail_log,x
    sta fail_log,x
    dex
    bpl -
    rts

PrintAllResults
    jsr InitKernalOutput
    jsr PrintClear

    lda pass1_fail_count
    beq .skip1
    lda #1
    sta print_pass_idx
    jsr RestorePass1FailLog
    jsr PrintPassHeader
    jsr PrintFailures
.skip1
    lda pass2_fail_count
    beq .done
    lda #2
    sta print_pass_idx
    jsr RestorePass2FailLog
    jsr PrintPassHeader
    jsr PrintFailures
.done
    jsr PrintPassTotals
    lda pass1_fail_count
    ora pass2_fail_count
    beq +
    lda #(RED + 24)
    sta $900f
    rts
+
    lda #<msg_ok
    ldy #>msg_ok
    jsr PrintString
    lda #(GREEN + 24)
    sta $900f
    rts

PrintPassTotals
    jsr PrintCr
    lda #<msg_p1
    ldy #>msg_p1
    jsr PrintString
    lda pass1_fail_count
    lsr
    jsr PrintHexByte
    lda #<msg_p2
    ldy #>msg_p2
    jsr PrintString
    lda pass2_fail_count
    lsr
    jsr PrintHexByte
    jmp PrintCr

PrintPassHeader
    lda print_pass_idx
    cmp #2
    beq .pass2
    lda #<msg_pass1
    ldy #>msg_pass1
    jsr PrintString
    jmp .hdr_fail
.pass2
    lda #<msg_pass2
    ldy #>msg_pass2
    jsr PrintString
.hdr_fail
    jsr PrintCr
    lda #<msg_fail
    ldy #>msg_fail
    jsr PrintString
    lda fail_count
    lsr
    jsr PrintHexByte
    jsr PrintCr
    rts

RunOnePass
    sta test_pattern
    jsr InitFailLog
    jsr DisableIrqLikeLoadRoom
    jsr FillFreeRegions
    jsr KernalLoadTestFile
    bcc +
    jsr LogLoadFailure
+
    jsr VerifyFreeRegions
    lda fail_count
    beq +
    sec
    rts
+
    clc
    rts

InitFailLog
    lda #0
    sta fail_count
    rts

DisableIrqLikeLoadRoom
    sei
    lda #$7f
    sta $911d
    sta $911e
    rts

InstallStopNoop
    lda #<StopNoop
    sta $0328
    lda #>StopNoop
    sta $0329
    rts

StopNoop
    lda #1
    rts

SaveEditorZp
    ldy #0
-
    lda $0094,y
    sta editor_zp_save,y
    iny
    cpy #editor_len_94
    bcc -
    lda $98
    sta editor_zp_save + editor_off_io
    lda $99
    sta editor_zp_save + editor_off_io + 1
    lda $9a
    sta editor_zp_save + editor_off_io + 2
    ldy #0
-
    lda $009b,y
    sta editor_zp_save + editor_off_9b,y
    iny
    cpy #editor_len_9b
    bcc -
    ldy #0
-
    lda $00c5,y
    sta editor_zp_save + editor_off_c5,y
    iny
    cpy #editor_len_c5
    bcc -
    ldy #0
-
    lda $0259,y
    sta editor_zp_save + editor_off_259,y
    iny
    cpy #editor_len_259
    bcc -
    rts

RestoreEditorZp
    ldy #0
-
    lda editor_zp_save,y
    sta $0094,y
    iny
    cpy #editor_len_94
    bcc -
    lda editor_zp_save + editor_off_io
    sta $98
    lda editor_zp_save + editor_off_io + 1
    sta $99
    lda editor_zp_save + editor_off_io + 2
    sta $9a
    ldy #0
-
    lda editor_zp_save + editor_off_9b,y
    sta $009b,y
    iny
    cpy #editor_len_9b
    bcc -
    ldy #0
-
    lda editor_zp_save + editor_off_c5,y
    sta $00c5,y
    iny
    cpy #editor_len_c5
    bcc -
    ldy #0
-
    lda editor_zp_save + editor_off_259,y
    sta $0259,y
    iny
    cpy #editor_len_259
    bcc -
    rts

InitKernalOutput
    ; IOINIT ($FDF9) only twiddles VIAs — it does not restore $0288/$9A.
    ; Canary prefill writes $55/$AA over editor ZP; restore our boot snapshot.
    jsr RestoreEditorZp
    jsr InstallStopNoop
    jsr DisableIrqLikeLoadRoom
    jsr $ffcc                   ; CLRCHN — default keyboard/screen, home cursor
    lda #3
    jsr $ffc9                   ; CHKOUT — screen after disk LOAD on LFN 15
    rts

PrintClear
    lda #147
    jsr $ffd2
    lda #19                     ; HOME — cursor to 0,0 after clear
    jmp $ffd2

PrintCr
    lda #13
    jmp $ffd2

PrintChar
    jmp $ffd2

PrintString
    sta ind_ptr
    sty ind_ptr + 1
    ldy #0
-
    lda (ind_ptr),y
    beq +
    jsr $ffd2
    iny
    bne -
+
    rts

KernalLoadTestFile
    lda #3
    ldx #<test_name
    ldy #>test_name
    jsr $ffbd
    lda #test_lfn
    ldx #test_device
    ldy #test_sa
    jsr $ffba
    lda #0
    jsr $ffd5
    php                         ; preserve LOAD carry through CLOSE
    lda #test_lfn
    jsr $ffc3                   ; CLOSE LFN 15 immediately after LOAD
    sei
    plp
    rts

LogLoadFailure
    lda fail_count
    cmp #max_fail_log_bytes
    bcs +
    tax
    lda #fail_load_mark
    sta fail_log,x
    sta fail_log + 1,x
    lda fail_count
    clc
    adc #2
    sta fail_count
+
    rts

LogFailureRegion
    stx log_x_offset
    sty log_y_table
    lda fail_count
    cmp #max_fail_log_bytes
    bcs +
    tax
    lda log_x_offset
    sta fail_log,x
    inx
    lda log_y_table
    sta fail_log,x
    inx
    stx fail_count
+
    ldx log_x_offset
    ldy log_y_table
    rts

FillFreeRegions
    lda test_pattern
    ldx #$8d
-
    sta $0002,x
    dex
    cpx #$ff
    bne -
    ldx #$12
-
    sta $009b,x
    dex
    cpx #$ff
    bne -
    ldx #$06
-
    sta $00b0,x
    dex
    cpx #$ff
    bne -
    ldx #$2f
-
    sta $00c5,x
    dex
    cpx #$ff
    bne -
    ldx #$08
-
    sta $00f7,x
    dex
    cpx #$ff
    bne -
    ldx #$bf
-
    sta $0100,x
    dex
    cpx #$ff
    bne -
    ldx #$58
-
    sta $0200,x
    dex
    cpx #$ff
    bne -
    ldx #$27
-
    sta $0277,x
    dex
    cpx #$ff
    bne -
    ldx #$5e
-
    sta $02a1,x
    dex
    cpx #$ff
    bne -
    ldx #$bf
-
    sta $033c,x
    dex
    cpx #$ff
    bne -
    rts

VerifyFreeRegions
    ldx #$8d
-
    lda $0002,x
    cmp test_pattern
    beq +
    ldy #0
    jsr LogFailureRegion
+
    dex
    cpx #$ff
    bne -
    ldx #$12
-
    lda $009b,x
    cmp test_pattern
    beq +
    ldy #1
    jsr LogFailureRegion
+
    dex
    cpx #$ff
    bne -
    ldx #$06
-
    lda $00b0,x
    cmp test_pattern
    beq +
    ldy #2
    jsr LogFailureRegion
+
    dex
    cpx #$ff
    bne -
    ldx #$2f
-
    lda $00c5,x
    cmp test_pattern
    beq +
    ldy #3
    jsr LogFailureRegion
+
    dex
    cpx #$ff
    bne -
    ldx #$08
-
    lda $00f7,x
    cmp test_pattern
    beq +
    ldy #4
    jsr LogFailureRegion
+
    dex
    cpx #$ff
    bne -
    ldx #$bf
-
    lda $0100,x
    cmp test_pattern
    beq +
    ldy #5
    jsr LogFailureRegion
+
    dex
    cpx #$ff
    bne -
    ldx #$58
-
    lda $0200,x
    cmp test_pattern
    beq +
    ldy #6
    jsr LogFailureRegion
+
    dex
    cpx #$ff
    bne -
    ldx #$27
-
    lda $0277,x
    cmp test_pattern
    beq +
    ldy #7
    jsr LogFailureRegion
+
    dex
    cpx #$ff
    bne -
    ldx #$5e
-
    lda $02a1,x
    cmp test_pattern
    beq +
    ldy #8
    jsr LogFailureRegion
+
    dex
    cpx #$ff
    bne -
    ldx #$bf
-
    lda $033c,x
    cmp test_pattern
    beq +
    ldy #9
    jsr LogFailureRegion
+
    dex
    cpx #$ff
    bne -
    rts

PrintFailures
    ldx #0
-
    cpx fail_count
    bcs +
    lda fail_log,x
    sta fail_range
    lda fail_log + 1,x
    sta fail_offset
    lda fail_range
    cmp #fail_load_mark
    bne .not_load
    lda fail_offset
    cmp #fail_load_mark
    bne .not_load
    lda #<msg_load
    ldy #>msg_load
    jsr PrintString
    jmp .next
.not_load
    jsr PrintFailureEntry
.next
    jsr PrintCr
    txa
    clc
    adc #2
    tax
    bne -
+
    rts

PrintFailureEntry
    ; fail_range = offset in range (X); fail_offset = region index (0..9)
    lda fail_offset
    asl
    tay
    lda region_bases,y
    clc
    adc fail_range
    sta scr_ptr_lo
    lda region_bases + 1,y
    adc #0
    sta scr_ptr_hi
    lda fail_offset
    jsr PrintHexByte
    lda #','
    jsr PrintChar
    lda fail_range
    jsr PrintHexByte
    lda #'/'
    jsr PrintChar
    lda scr_ptr_lo
    sta ind_ptr
    lda scr_ptr_hi
    sta ind_ptr + 1
    ldy #0
    lda (ind_ptr),y
    jsr PrintHexByte
    rts

PrintHexByte
    sta hex_temp
    lda hex_temp
    lsr
    lsr
    lsr
    lsr
    jsr NibbleToChar
    jsr PrintChar
    lda hex_temp
    and #$0f
    jsr NibbleToChar
    jmp PrintChar

NibbleToChar
    cmp #10
    bcc +
    adc #'A' - 10 - 1
    rts
+
    adc #'0'
    rts

PassHalt
    jmp PassHalt

FailHalt
    lda #(PURPLE + 24)
    sta $900f
    jmp FailHalt

!source "loadram_payload.inc"
