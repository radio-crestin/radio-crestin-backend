import {Button} from "@chakra-ui/react";
import React from "react";

export default function RandomStationButton({pickARandomStation}: any) {
  return (
    <Button
      name="Selecteaza o statie random"
      w={{base: '45px', lg: '50px'}}
      h={{base: '45px', lg: '50px'}}
      p={'13px'}
      bg={'#ffc107'}
      _hover={{bg: '#ffcf40'}}
      borderRadius={'40px'}
      onClick={pickARandomStation}>
      <svg
        width="50" height="50"
        focusable="false" aria-hidden="true" viewBox="0 0 24 24"
        data-testid="ElectricBoltIcon">
        <path
          fill="white"
          d="M14.69 2.21 4.33 11.49c-.64.58-.28 1.65.58 1.73L13 14l-4.85 6.76c-.22.31-.19.74.08 1.01.3.3.77.31 1.08.02l10.36-9.28c.64-.58.28-1.65-.58-1.73L11 10l4.85-6.76c.22-.31.19-.74-.08-1.01-.3-.3-.77-.31-1.08-.02z"/>
      </svg>
    </Button>
  )
}
