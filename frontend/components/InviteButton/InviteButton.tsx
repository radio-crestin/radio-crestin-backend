import React, {useEffect} from "react";

import {
  Button,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalHeader,
  ModalOverlay, SimpleGrid,
  Text,
  useDisclosure
} from "@chakra-ui/react";
import {
  EmailIcon,
  EmailShareButton,
  FacebookIcon,
  FacebookShareButton, TelegramIcon, TelegramShareButton,
  TwitterIcon,
  TwitterShareButton,
  ViberIcon,
  ViberShareButton,
  WhatsappIcon,
  WhatsappShareButton,
} from "react-share";
import {withRouter} from "next/router";

function InviteButton() {
  const { isOpen, onOpen, onClose } = useDisclosure()
  const shareTitle = "Asculta si tu acest radio"
  let shareUrl = "";
  // useEffect(() => {
  //   shareUrl = window.location.href
  // }, [])

  return  (
    <>
      <Button colorScheme='blue' borderRadius={{base: '10px', lg: '30px'}} onClick={onOpen}>
        Recomandă unui prieten
      </Button>

      <Modal isOpen={isOpen} onClose={onClose} size={'lg'} preserveScrollBarGap={true}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Recomandă unui prieten</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <SimpleGrid columns={6} spacing={2} w={'60%'} mt={3} mb={8}>
              <FacebookShareButton title={shareTitle} url={shareUrl} >
                <FacebookIcon size={32} round />
              </FacebookShareButton>
              <TwitterShareButton title={shareTitle} url={shareUrl} >
                <TwitterIcon size={32} round />
              </TwitterShareButton>
              <TelegramShareButton title={shareTitle} url={shareUrl} >
                <TelegramIcon size={32} round />
              </TelegramShareButton>
              <WhatsappShareButton title={shareTitle} url={shareUrl} >
                <WhatsappIcon size={32} round />
              </WhatsappShareButton>
              <ViberShareButton title={shareTitle} url={shareUrl} >
                <ViberIcon size={32} round />
              </ViberShareButton>
              <EmailShareButton subject={shareTitle} url={shareUrl} >
                <EmailIcon size={32} round />
              </EmailShareButton>
            </SimpleGrid>
          </ModalBody>
        </ModalContent>
      </Modal>
    </>
  )
}
export default withRouter(InviteButton)
