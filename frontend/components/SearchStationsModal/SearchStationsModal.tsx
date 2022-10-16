import {
  Flex,
  GridItem,
  Input,
  InputGroup,
  InputLeftElement,
  Link,
  Modal,
  ModalBody,
  ModalContent,
  ModalOverlay,
  useDisclosure,
} from "@chakra-ui/react";
import React, { useState } from "react";
import { Station } from "../../types";
import { SearchIcon } from "@chakra-ui/icons";

export function SearchStationsModal({ stations }: { stations: Station[] }) {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [filteredItems, setFilteredItems]: Station[] | any = useState(stations);
  return (
    <>
      <Link onClick={onOpen}>
        <InputGroup>
          <InputLeftElement
            pointerEvents="none"
            height={"full"}
            children={<SearchIcon color="black" />}
          />
          <Input
            placeholder="Tasteaza numele statiei"
            size="lg"
            mt={{ base: 5, md: 0 }}
            width={{ base: "100%", md: 270, lg: 350 }}
          />
        </InputGroup>
      </Link>

      <Modal isOpen={isOpen} onClose={onClose} size={"3xl"}
             preserveScrollBarGap={true}>
        <ModalOverlay />
        <ModalContent>
          <Input
            placeholder="Tasteaza numele statiei"
            size="lg"
            width={{ base: "100%" }}
            onChange={e => {
              let filterText = e.target.value.toString().toLowerCase();
              let dataFiltered = stations.filter(
                item =>
                  item.title.toLowerCase().toString().includes(filterText) &&
                  item,
              );
              setFilteredItems(dataFiltered);
            }}
          />
          <ModalBody maxHeight={600} overflow="auto">
            {filteredItems.length > 0 ? (
              <Flex flexDirection={"column"}>
                {filteredItems.map((station: any) => (
                  <Link href={station.slug} py={2} key={station.title}>
                    <a>{station.title}</a>
                  </Link>
                ))}
              </Flex>
            ) : (
              <GridItem as="div" colSpan={5} py={2}>
                Nu există nici o stație cu acest nume.
              </GridItem>
            )}
          </ModalBody>
        </ModalContent>
      </Modal>
    </>
  );
}
