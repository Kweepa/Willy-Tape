; One-shot boot at end of PRG (below image_base; not overwritten by room load).
; sei -> VIA #2 IER/T2CL -> stack -> IOINIT -> VIC init -> copy tables -> jmp start_game
; Must not RTS here: txs clears the SYS return address on the stack.

WarmStart
 
    lda #$7f
    sta $911d                   ; VIA #2 IER - disable all enables
    sta $911e                   ; T2CL - preset timer 2 low

    cld                         ; clear bcd mode
    ldx #$ff                    ; reset stack
    txs

    jsr $fdf9                   ; IOINIT
    sei

    ; $eb15 is minimal no-op interrupt handler
    lda #$15
    sta $0314
    lda #$eb
    sta $0315

    ldx #5                      ; initialize vic registers
-
    lda init24_val,x
    sta $9000,x
    dex
    bpl -

    ldx #boot_zp_room_size - 1  ; cell_off..draw_vguard at $DC
-
    lda boot_zp_pack,x
    sta cell_off_2x3,x
    dex
    bpl -

    lda #10     ; set volume
    sta $900e

    ldx #4      ; clear voices
    lda #0
-
    sta $900a-1,x
    dex
    bne -

    jsr RelocateDrawPlayerTables
    jsr RelocateRopeXadd

    ldx #reloc_a_size - 1
-
    lda reloc_a_src,x
    sta RELOC_A_BASE,x
    dex
    bpl -

    ldx #reloc_b_size - 1
-
    lda reloc_b_src,x
    sta RELOC_B_BASE,x
    dex
    bpl -

    ldx #reloc_c_size - 1
-
    lda reloc_c_src,x
    sta RELOC_C_BASE,x
    dex
    bpl -

    ldx #reloc_d_size - 1
-
    lda reloc_d_src,x
    sta RELOC_D_BASE,x
    dex
    bpl -

    ldx #reloc_e_size - 1
-
    lda reloc_e_src,x
    sta RELOC_E_BASE,x
    dex
    bpl -

    ldx #stack_page_size - 1    ; x24rowtab..jumpnotes at $140+
-
    lda stack_page_pack,x
    sta x24rowtab,x
    dex
    bpl -

    ldx #ingame_tune_pitch_rom_bytes - 1
-
    lda ingame_tune_pitch_rom,x
    sta ingame_tune_pitch,x
    dex
    bpl -

    ldx #ingame_tune_idx_rom_bytes - 1
-
    lda ingame_tune_idx_rom,x
    sta INGAME_TUNE_SEQ,x
    dex
    bpl -

    jmp start_game

; Copy draw_player tables to $37/$3D (off KERNAL keyboard ptr $F5/$F6 during LOAD).
RelocateDrawPlayerTables
    ldx #5
-
    lda boot_draw_player_offsets,x
    sta draw_player_offsets,x
    lda boot_draw_player_chrs,x
    sta draw_player_chrs,x
    dex
    bpl -
    rts

; Copy rope_xadd to cassette buffer $35C (survives KERNAL disk LOAD).
RelocateRopeXadd
    ldx #boot_rope_xadd_size - 1
-
    lda boot_rope_xadd_pack,x
    sta ROPE_XADD,x
    dex
    bpl -
    rts

init24_val
    !byte $0a, $32, $98, $22, $00, $ff
