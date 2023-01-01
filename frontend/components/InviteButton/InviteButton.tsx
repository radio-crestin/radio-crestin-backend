import React, {useEffect, useState} from "react";

import {
  Button,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalHeader,
  ModalOverlay,
  SimpleGrid,
  useDisclosure
} from "@chakra-ui/react";
import {
  EmailIcon,
  EmailShareButton,
  FacebookIcon,
  FacebookShareButton,
  TelegramIcon,
  TelegramShareButton,
  TwitterIcon,
  TwitterShareButton,
  ViberIcon,
  ViberShareButton,
  WhatsappIcon,
  WhatsappShareButton,
} from "react-share";
import {withRouter} from "next/router";

function InviteButton() {
  const {isOpen, onOpen, onClose} = useDisclosure()
  const shareTitle = "Te invit să asculți acest radio: "
  const [shareUrl, setShareUrl] = useState("")
  useEffect(() => {
    setShareUrl(window.location.href)
  }, [])

  return (
    <>
      <Button
        name="Invita un prieten"
        w={{base: '45px', lg: '50px'}}
        h={{base: '45px', lg: '50px'}}
        p={'13px'}
        bg={'#1e77f2'}
        _hover={{bg: '#2e7cfc'}}
        borderRadius={'40px'}
        onClick={onOpen}>
        <svg
          width="50" height="50"
          focusable="false" aria-hidden="true" viewBox="0 0 24 24">
          <path fill="white"
                d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92 1.61 0 2.92-1.31 2.92-2.92s-1.31-2.92-2.92-2.92z"></path>
        </svg>
      </Button>

      <Modal isOpen={isOpen} onClose={onClose} size={'lg'}
             preserveScrollBarGap={true}>
        <ModalOverlay/>
        <ModalContent>
          <ModalHeader>Recomandă unui prieten</ModalHeader>
          <ModalCloseButton/>
          <ModalBody>
            <SimpleGrid columns={6} spacing={2} w={'60%'} mt={3} mb={8}>
              <FacebookShareButton title={shareTitle} url={shareUrl}>
                <FacebookIcon size={32} round/>
              </FacebookShareButton>
              <TwitterShareButton title={shareTitle} url={shareUrl}>
                <TwitterIcon size={32} round/>
              </TwitterShareButton>
              <TelegramShareButton title={shareTitle} url={shareUrl}>
                <TelegramIcon size={32} round/>
              </TelegramShareButton>
              <WhatsappShareButton title={shareTitle} url={shareUrl}>
                <WhatsappIcon size={32} round/>
              </WhatsappShareButton>
              <ViberShareButton title={shareTitle} url={shareUrl}>
                <ViberIcon size={32} round/>
              </ViberShareButton>
              <EmailShareButton subject={shareTitle} url={shareUrl}>
                <EmailIcon size={32} round/>
              </EmailShareButton>
            </SimpleGrid>
          </ModalBody>
        </ModalContent>
      </Modal>
    </>
  )
}

export default withRouter(InviteButton)
