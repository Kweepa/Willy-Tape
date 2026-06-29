!zone guardians_implementation

CopyDownGuardianData
    jsr CalcGuardianRecPtr
    ldy #g_off_axis
-
    lda (arr),y
    sta hx,y
    dey
    bpl -
    rts

GetHorizontalGuardianFramePtr
    lda hx
    and #$03
    ldx g_fctl ; check bidirectional
    beq +
    ldx hd ; if going left, want to use the first four frames
    bmi ++
    eor #4 ; otherwise use the next four
+
    bpl ++

GetVerticalGuardianFramePtr
    lda g_frame
++
    clc
    adc ht
    jmp GetSpriteFrameAddr   ; tail call — rts resumes at caller after jsr ResolveGuardianFramePtr

MoveGuardian
    ; advance either x or y
    ldx guard_axis
    lda hx,x
    clc
    adc hd
    sta hx,x
    tay

    ; convert hd into a 0 or 1 index in x
    ldx #0
    lda hd
    bmi +
    inx
+
    ; compare left or right extent against new coord stored in y
    tya
    cmp hl,x
    bne +

    lda hd     ; flip direction
    eor #$ff
    clc
    adc #1
    sta hd
+
    inc g_frame
    lda g_frame
    and g_fctl
    sta g_frame
    rts

DrawGuardian
    ldx guard_axis
    inc hguard_count,x

    ldx hx
    ldy hy
    jsr ConvertXYToScreenAddr

    ldx #3
    lda hy
    and #7
    beq draw_guard_loop
    inx
    inx
draw_guard_loop
-
    ldy cell_off_2x3,x
    lda hc
    sta (col_ptr),y
    lda draw_vguard_chrs,x
    clc
    adc guard_udg_index
    sta (scr_ptr),y
    dex
    bpl -
    rts

; arr = sprite_frames + (frame index) * 32. Uses ht/g_frame/axis —
; must not rely on arr left over from CalcGuardianRecPtr (meta guardian tail).
ResolveGuardianFramePtr
    lda guard_axis
    bne +
    jmp GetHorizontalGuardianFramePtr ; tail call
+
    jmp GetVerticalGuardianFramePtr ; tail call

; CopyGuardianFrame — copy one 32-byte pool frame into this guardian's 6-char UDG slot.
;
; Call chain (MoveGuardians, move tick only):
;   CopyDownGuardianData  -> hx..guard_axis from guardian_data_base record
;   MoveGuardian          -> may advance hx/hy, hd, g_frame
;   CalcGuardianUDGAddr   -> arr2 = dest base (see below)
;   CopyGuardianFrame
;
; ZP inputs (guardian scratch $20-$29, plus guard_udg_off $48):
;   hx, hy     — pixel position (hy & 7 used for vertical trim within cell)
;   ht         — pool frame index of set's first frame (runtime byte 6 / g_off_fmin)
;   g_frame    — animation frame counter (byte 5); vertical lookup adds this to ht
;   g_fctl     — horizontal: 0 uni / 1 bidir; vertical: g_frame AND mask (byte 7)
;   hd         — horizontal velocity sign; bidir frame pick uses hd bit 7
;   guard_axis — 0 horizontal (frame from hx & 3), 1 vertical (frame from g_frame)
;   guard_udg_off — guardian_index * 6 (which 6-char UDG block in guardian_udgs)
;
; arr on entry: stale — do not use. ResolveGuardianFramePtr overwrites it.
; arr on exit:  pointer to selected sprite_frames row (column-major 32 B frame):
;                bytes 0-15  left column (16 rows)
;                bytes 16-31 right column (16 rows)
;   Horizontal: index = (hx & 3) [+4 if bidir and hd >= 0] + ht
;   Vertical:   index = g_frame + ht
;   Then GetSpriteFrameAddr: arr = sprite_frames + index * 32
;
; arr2 on entry: set by CalcGuardianUDGAddr immediately before this call.
;   arr2 -> guardian_udgs + guard_udg_off * 8
;        (= udg_base + GUARDIAN_CHR*8 + guardian_index*48)
;   Top-left byte of this guardian's 6-character workspace (2 wide x 3 tall).
;
; arr3: local only — arr2 + 24 (top right char in that 6-char block, i.e. +3 slots).
;   Used as the destination pointer for the right sprite column while arr2 receives
;   the left column. Both are filled row-by-row with Y as the running offset.
;
; Algorithm:
;   1. ResolveGuardianFramePtr -> arr = source frame in catalogue sprite_frames
;   2. Patch mod_src_col1/2 absolute LDA operands to arr and arr+16
;   3. If hy & 7 != 0: clear (hy & 7) leading rows in both dest columns with 0
;   4. Copy 16 rows: left column from mod_src_col1 -> (arr2),y; right from mod_src_col2 -> (arr3),y
;   5. Clear (7 - (hy & 7)) trailing rows in both columns with 0
; DrawGuardian then stamps screen chars guard_udg_index+0..5 onto the playfield.
CopyGuardianFrame
    jsr ResolveGuardianFramePtr

    lda arr2
    clc
    adc #24
    sta arr3
    lda arr2+1
    adc #0
    sta arr3+1
    lda arr
    sta mod_src_col1+1
    clc
    adc #16
    sta mod_src_col2+1
    lda arr+1
    sta mod_src_col1+2
    adc #0
    sta mod_src_col2+2

    ldy #0

    lda hy
    and #7
    beq +
    tax

    lda #0
-
    sta (arr2),y
    sta (arr3),y
    iny
    dex
    bne -
+
    ldx #16
-
mod_src_col1
    lda sprite_frames
    inc mod_src_col1+1
    bne +
    inc mod_src_col1+2
+
    sta (arr2),y
mod_src_col2
    lda sprite_frames
    inc mod_src_col2+1
    bne +
    inc mod_src_col2+2
+
    sta (arr3),y
    iny
    dex
    bne -

    lda hy
    and #7
    eor #7
    tax

    lda #0
-
    sta (arr2),y
    sta (arr3),y
    iny
    dex
    bpl -

    rts

MoveGuardians
    lda meta_content_guardians
    beq move_guardians_done
    lda #0
    sta guardian_index
    sta hguard_count
    sta vguard_count
--
    ; UDG slot from guardian_index (inlined CalcGuardianUDGIndex)
    ; multiply by 6
    lda guardian_index
    asl
    adc guardian_index  ; asl clears C
    asl
    sta guard_udg_off
    adc #GUARDIAN_CHR ; asl clears C
    sta guard_udg_index

    jsr CopyDownGuardianData
    lda guard_axis
    bne +
    jsr ShouldMoveHorizontalGuardianThisFrame
    bne draw_guardian
    beq move_guardian
+
    jsr ShouldMoveVerticalGuardianThisFrame
    bne draw_guardian
move_guardian
    jsr MoveGuardian
    jsr CalcGuardianUDGAddr
    jsr CopyGuardianFrame
draw_guardian
    jsr DrawGuardian
    jmp EndGuardianLoop

EndGuardianLoop

    ; CopyUpGuardianData
    jsr CalcGuardianRecPtr
    ldy #g_off_frame
-
    lda hx,y
    sta (arr),y
    dey
    bpl -

    +BorderDebugGuardianIndex
    inc guardian_index
    lda guardian_index
    cmp meta_content_guardians
    bne --
move_guardians_done
    rts

ShouldMoveHorizontalGuardianThisFrame
    lda hguard_count
    and #3
    cmp left_right_ctr
    rts

ShouldMoveVerticalGuardianThisFrame
    lda vguard_count
    cmp up_down_ctr
    beq +
    sec
    sbc #3
    cmp up_down_ctr
+
    rts

draw_vguard_chrs
    !byte 0, 3, 1, 4, 2, 5                            ; DrawGuardian
