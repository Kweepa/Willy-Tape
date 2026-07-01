; Arrow glyphs @ chr 64–65 ($1A00) — PRG-resident, not copied per room load.

arrow_udg_ltr
    !byte 0, 0, 194, 127, 194, 0, 0, 0
arrow_udg_rtl
    !byte 0, 0, 67, 254, 67, 0, 0, 0

!if arrow_udg_ltr <> high_bank {
!error "arrow_udg_ltr must be at high_bank ($1A00)"
}
!if arrow_udg_rtl <> high_bank + 8 {
!error "arrow_udg_rtl must be chr 65 ($1A08)"
}
