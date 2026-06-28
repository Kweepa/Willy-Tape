!source header.asm
!source relocated_code.asm
!warn "reloc_a_size = ", reloc_a_size
!warn "reloc_a_end = $", hex(RELOC_A_BASE + reloc_a_size - 1)
!warn "reloc_a_slack = ", RELOC_A_LIMIT - RELOC_A_BASE - reloc_a_size
!warn "reloc_c_size = ", reloc_c_size
!warn "reloc_c_end = $", hex(RELOC_C_BASE + reloc_c_size - 1)
!warn "reloc_b_size = ", reloc_b_size
!warn "reloc_b_end = $", hex(RELOC_B_BASE + reloc_b_size - 1)
!warn "reloc_e_size = ", reloc_e_size
!warn "reloc_e_end = $", hex(RELOC_E_BASE + reloc_e_size - 1)
