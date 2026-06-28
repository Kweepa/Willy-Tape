; If I Were a Rich Man — ROM tables copied at WarmStart.
; Pitch: VIC $900B values (C=135 .. C=195). Index: 0-8 into pitch table.

ingame_tune_pitch_rom
	!byte 135,159,163,175,179,183,187,191,195
ingame_tune_pitch_rom_end = *
ingame_tune_pitch_rom_bytes = ingame_tune_pitch_rom_end - ingame_tune_pitch_rom

ingame_tune_idx_rom
	!byte 3,2,3,2,1,1,0,0,0,0,1,2,3,2,3,2
	!byte 1,2,3,5,6,5,6,5,3,3,3,3,3,3,3,3
	!byte 8,8,8,8,7,7,5,5,3,2,1,2,3,3,1,1
	!byte 4,3,2,3,4,4,2,2,8,8,8,8,8,8,8,8
ingame_tune_idx_rom_end = *
ingame_tune_idx_rom_bytes = ingame_tune_idx_rom_end - ingame_tune_idx_rom

!if ingame_tune_pitch_rom_bytes <> 9 {
!error "ingame_tune_pitch_rom must be 9 bytes"
}
!if ingame_tune_idx_rom_bytes <> 64 {
!error "ingame_tune_idx_rom must be 64 bytes"
}
