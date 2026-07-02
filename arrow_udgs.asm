; chr 64-65 @ $1A00 — runtime player UDG scratch (not PRG-resident).
; Arrow glyphs @ chr 66-67 ($1A10) — PRG-resident, not copied per room load.

!zone arrow_udgs

resident_pad
    !fill 16, 0

arrow_udg_ltr
    !byte 0, 0, 194, 127, 194, 0, 0, 0
arrow_udg_rtl
    !byte 0, 0, 67, 254, 67, 0, 0, 0

hud_udg_men
    !byte 60, 60, 126, 52, 62, 60, 24, 60
hud_udg_item
    !byte 4, 4, 174, 174, 162, 66, 66, 238

!if arrow_udg_ltr <> resident_base {
!error "arrow_udg_ltr must be at resident_base ($1A10)"
}
!if arrow_udg_rtl <> resident_base + 8 {
!error "arrow_udg_rtl must be chr 67 ($1A18)"
}
