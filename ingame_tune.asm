; In-game pitch table from the original Spectrum tune (C=150 .. C=210).
; Pitch: $900B values written by PlayInGameMusic (registers A/B/C map to 0/2/4 in index).
; Index: seq nybbles select pitch index 0-8; tape port reads pitch from PRG below.

!zone ingame_tune

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

ingame_tune_pitch = ingame_tune_pitch_rom

!if ingame_tune_pitch_rom_bytes <> 9 {
!error "ingame_tune_pitch_rom must be 9 bytes"
}
!if ingame_tune_idx_rom_bytes <> 64 {
!error "ingame_tune_idx_rom must be 64 bytes"
}
