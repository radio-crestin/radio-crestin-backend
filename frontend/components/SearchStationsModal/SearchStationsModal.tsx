import Link from 'next/link';
import React, {useState} from 'react';
import {
  Button,
  Flex,
  GridItem,
  Input,
  InputGroup,
  InputLeftElement,
  Modal,
  ModalBody,
  ModalContent,
  ModalOverlay,
  useDisclosure,
} from '@chakra-ui/react';
import {Station, StationGroup} from '../../types';
import {SearchIcon} from '@chakra-ui/icons';

export function SearchStationsModal({
  station_group,
  stations,
}: {
  station_group: StationGroup;
  stations: Station[];
}) {
  const {isOpen, onOpen, onClose} = useDisclosure();
  const [filteredItems, setFilteredItems]: Station[] | any = useState(stations);
  return (
    <>
      <InputGroup
        as={'button'}
        border={'solid'}
        borderWidth={'1'}
        borderColor={'black'}
        cursor={'pointer'}
        p={2}
        borderRadius={15}
        onClick={onOpen}
        width={'fit-content'}>
        <SearchIcon color="black" />
      </InputGroup>

      <Modal
        isOpen={isOpen}
        onClose={onClose}
        size={'3xl'}
        preserveScrollBarGap={true}>
        <ModalOverlay />
        <ModalContent p={5}>
          <InputGroup mb={5}>
            <InputLeftElement
              pointerEvents="none"
              height={'full'}
              children={<SearchIcon color="black" />}
            />
            <Input
              placeholder="Tasteaza numele statiei"
              size="lg"
              width={{base: '100%'}}
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
          </InputGroup>
          <ModalBody
            maxHeight={{base: 'calc(100vh - 230px)', sm: 600}}
            overflow="auto"
            p={0}
            pr={3}>
            {filteredItems.length > 0 ? (
              <Flex flexDirection={'column'}>
                {filteredItems.map((station: Station) => (
                  <Link
                    href={`/${encodeURIComponent(
                      station_group?.slug,
                    )}/${encodeURIComponent(station.slug)}`}
                    onClick={() => {
                      onClose();
                      setFilteredItems(stations);
                    }}
                    key={station.title}>
                    <Button
                      background={'white'}
                      _hover={{background: '#00000013', borderRadius: 10}}
                      px={2}
                      py={3}
                      m={1}
                      justifyContent={'flex-start'}
                      fontWeight={'normal'}
                      width={'100%'}>
                      {station.title}
                    </Button>
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
