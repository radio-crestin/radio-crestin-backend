import React, {useState} from 'react';

import FacebookIcon from '@/public/facebook.svg';
import {
  Button,
  Flex,
  FormControl,
  FormLabel,
  Image,
  Link,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Text,
  Textarea,
  useDisclosure,
  useToast,
} from '@chakra-ui/react';
import {ExternalLinkIcon} from '@chakra-ui/icons';
// @ts-ignore
import ReactStars from 'react-rating-stars-component';
import {postReviewClientSide} from '../../frontendServices/review';

export default function StationInformation(props: any) {
  const {station} = props;
  const average = (arr: any[]) => arr.reduce((a, b) => a + b, 0) / arr.length;
  const StationRating =
    Math.round(
      (average(station?.reviews?.map((i: any) => i.stars) || []) || 0) * 10,
    ) / 10;
  const numberOfListeners = station?.total_listeners
    ? station?.total_listeners + 1
    : null;
  const latestPost = station.posts[0];
  const toast = useToast();

  const [userReviewStars, setUserReviewStars] = useState(5);
  const [userReviewMessage, setUserReviewMessage] = useState('');
  const {isOpen, onOpen, onClose} = useDisclosure();

  const initialRef = React.useRef<HTMLTextAreaElement>(null);

  const submitReviewMessage = async () => {
    onClose();
    const {done} = await postReviewClientSide({
      user_name: null,
      station_id: station.id,
      stars: userReviewStars,
      message: userReviewMessage,
    });
    if (done) {
      toast({
        title: 'Review-ul a fost încărcat cu success.',
        description: 'Vă mulțumim frumos!',
        status: 'success',
        position: 'top',
        duration: 4000,
        isClosable: true,
      });
    } else {
      toast({
        title: 'A apărut o eroare neașteptată.',
        description: 'Vă rugăm să încercați mai târziu!',
        status: 'error',
        position: 'top',
        duration: 4000,
        isClosable: true,
      });
    }
  };

  return (
    <Flex direction={'column'} pl={{base: 0, lg: 4}}>
      <Text
        as="h1"
        fontSize={{base: '2xl', lg: '5xl'}}
        mt={{base: 1, lg: 0}}
        noOfLines={1}
        fontWeight="bold">
        {station.title}
      </Text>

      <Flex>
        <ReactStars
          key={`rating-${station.id}`}
          count={5}
          onChange={(rating: number) => {
            setUserReviewStars(rating);
            setUserReviewMessage('');
            onOpen();
          }}
          size={20}
          value={StationRating}
          isHalf={true}
          activeColor="#fe7f38"
        />
        {/* @ts-ignore */}
        {StationRating !== 0 && (
          <Text fontSize={'md'} lineHeight={'30px'} ml={1}>
            {StationRating}/5
          </Text>
        )}
        {station.facebook_page_id && (
          <Link
            href={'https://facebook.com/' + station.facebook_page_id}
            isExternal>
            <Image
              src={FacebookIcon.src}
              alt={'Facebook page'}
              height={22}
              width={22}
              htmlHeight={22}
              htmlWidth={22}
              m={'4px'}
              ml={1.5}
              draggable={false}
            />
          </Link>
        )}
      </Flex>

      {numberOfListeners && (
        <Text fontSize={{base: 'sm', lg: 'md'}}>
          {numberOfListeners} persoane ascultă împreună cu tine acest radio
        </Text>
      )}

      <>
        <Text
          as="h2"
          fontSize={{base: 'md', lg: 'xl'}}
          mt={{base: 4, lg: 6}}
          maxW={{base: '100%', lg: '80%'}}
          noOfLines={1}
          fontWeight="bold">
          {latestPost ? latestPost.title : station.title}
        </Text>
        <Text
          fontSize={{base: 'md', lg: 'xl'}}
          mt="1"
          noOfLines={{base: 5, lg: 3}}
          maxW={{base: '100%', lg: '90%'}}>
          {latestPost ? latestPost.description : station.description}
        </Text>
        <Link
          href={latestPost ? latestPost.link : station.website}
          mt={{base: 2, lg: 3}}
          fontSize={'md'}
          isExternal>
          {latestPost && latestPost.link
            ? 'Continuă citirea articolului'
            : 'Vizitează site-ul web'}{' '}
          <ExternalLinkIcon mx="2px" width={4} height={4} />
        </Link>
      </>

      <Modal
        initialFocusRef={initialRef}
        isOpen={isOpen}
        onClose={onClose}
        preserveScrollBarGap={true}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Adauga un mesaj recenziei</ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            <FormControl>
              <FormLabel>Mesajul dumneavoastra</FormLabel>
              <Textarea
                ref={initialRef}
                placeholder="Introduceți mesajul dumneavoastră aici.."
                onChange={e => {
                  setUserReviewMessage(e.target.value);
                }}
                size="sm"
                resize={'none'}
              />
            </FormControl>
          </ModalBody>

          <ModalFooter>
            <Button colorScheme="blue" mr={3} onClick={submitReviewMessage}>
              Trimite
            </Button>
            <Button onClick={submitReviewMessage}>Închide</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Flex>
  );
}
