; Reloc island 2 source — high bank PRG; copied to $036C at WarmStart.

!zone tape_reloc_lo2

reloc_lo2_src
!pseudopc RELOC_LO2_BASE {

GetSpriteFrameAddr
    ldx #0
    stx arr+1
    ldx #5
-
    asl
    rol arr+1
    dex
    bne -
    clc
    adc #<sprite_frames
    sta arr
    lda arr+1
    adc #>sprite_frames
    sta arr+1
    rts

CalcGuardianUDGAddr
    lda guard_udg_off
    asl
    asl
    asl
    clc
    adc #<guardian_udgs
    sta arr2
    lda #>guardian_udgs
    adc #0
    sta arr2+1
    rts

LoadOneUdgChr
    asl
    asl
    asl
    sta udg_ptr ; udg_base is page aligned
    ; when we do this it's always a udg < 32
    lda #>udg_base
    sta udg_ptr+1
    ldy #7
-
    lda (stream_ptr),y
    sta (udg_ptr),y
    dey
    bpl -

    lda #8
    clc
    adc stream_ptr
    sta stream_ptr
    bcc +
    inc stream_ptr_hi
+
    rts


}
reloc_lo2_size = * - reloc_lo2_src
!if reloc_lo2_size > RELOC_LO2_MAX {
!error "reloc island 2 overflow"
}
