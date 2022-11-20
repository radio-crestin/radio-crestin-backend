import React, {useEffect, useState} from 'react';
import ReactPlayer from 'react-player/lazy';
import {useRouter} from 'next/router';
import {useIdleTimer} from 'react-idle-timer';
import {isDesktop, isMobile} from 'react-device-detect';

import {
  Box,
  Flex,
  Image,
  Slider,
  SliderFilledTrack,
  SliderThumb,
  SliderTrack,
  Spacer,
  Text,
} from '@chakra-ui/react';

import {useLocalStorageState} from '@/utils/state';
import {cdnImageLoader} from '@/utils/cdnImageLoader';
import {trackListenClientSide} from '../frontendServices/listen';
import {CONSTANTS} from '../lib/constants';
import {Station} from '../types';

const STREAM_TYPE_INFO: any = {
  HLS: {
    field: 'hls_stream_url',
    name: 'hls',
  },
  PROXY: {
    field: 'proxy_stream_url',
    name: 'proxy',
  },
  ORIGINAL: {
    field: 'stream_url',
    name: 'original',
  },
};
const MAX_MEDIA_RETRIES = 20;

export default function StationPlayer({stations}: any) {
  const {station_slug} = useRouter().query;
  const [retries, setRetries] = useState(MAX_MEDIA_RETRIES);
  const [isMuted, setMuted] = useState(true);
  const [isPlaying, setPlaying] = useLocalStorageState(false, 'IS_PLAYING');
  const [volume, setVolume] = useLocalStorageState(60, 'AUDIO_PLAYER_VOLUME');
  const [selectedStreamType, setSelectedStreamType] = useState('HLS');
  const [hasInteracted, setInteraction] = useState(false);

  useIdleTimer({
    onAction: () => setInteraction(true),
  });

  useEffect(() => {
    if (isMobile && !hasInteracted) {
      setPlaying(false);
    }
  }, []);

  const station: Station = stations.find(
    (station: {slug: string}) => station.slug === station_slug,
  );

  if (!station) {
    return <></>;
  }

  // TODO: we might need to populate these from local storage
  const retryMechanism = async () => {
    console.debug('retryMechanism called');
    setRetries(retries - 1);
    console.debug('remaining retries: ', retries);
    if (retries > 0) {
      setSelectedStreamType('');
      await new Promise(r => setTimeout(r, 200));

      if (selectedStreamType === 'HLS') {
        setSelectedStreamType('PROXY');
        console.debug('waiting 1s');
        await new Promise(r => setTimeout(r, 1000));
        return true;
      }
      if (selectedStreamType === 'PROXY') {
        setSelectedStreamType('ORIGINAL');
        console.debug('waiting 1s');
        await new Promise(r => setTimeout(r, 1000));
        return true;
      }
      if (selectedStreamType === 'ORIGINAL') {
        setSelectedStreamType('HLS');
        console.debug('waiting 1s');
        await new Promise(r => setTimeout(r, 1000));
        return true;
      }
    }
    return false;
  };

  const station_url =
    selectedStreamType !== ''
      ? // @ts-ignore
        station[STREAM_TYPE_INFO[selectedStreamType as string].field]
      : '';

  useEffect(() => {
    if ('mediaSession' in navigator) {
      if (isPlaying) {
        navigator.mediaSession.metadata = new MediaMetadata({
          title: station.now_playing?.song?.name || station.title,
          artist: station.now_playing?.song?.artist.name || '',
          artwork: [
            {
              src: station.thumbnail_url || CONSTANTS.DEFAULT_COVER,
              sizes: '512x512',
              type: 'image/png',
            },
          ],
        });
      } else {
        navigator.mediaSession.metadata = new MediaMetadata({});
      }
    }
  }, [station]);

  // TODO: when the user click play, increase the number of listeners by 1
  // Also, delay the updated by 500 ms, also optional we can add an animation when we update the listeners counter.. to emphasis it
  // TODO: make the player mobile responsive

  useEffect(() => {
    if (isPlaying) {
      trackListenClientSide({
        station_id: station.id as unknown as bigint,
        info: {},
      });
    }
    const timer = setInterval(() => {
      if (isPlaying) {
        trackListenClientSide({
          station_id: station.id as unknown as bigint,
          info: {},
        });
      }
    }, 30 * 1000);
    return () => clearInterval(timer);
  }, [isPlaying]);

  return (
    <Box
      w={{base: '100%'}}
      h={{base: 'auto'}}
      minW={{base: 'auto'}}
      maxW={'500px'}
      pl={{base: 0}}
      position={{base: 'fixed'}}
      bottom={{base: 0}}
      right={0}
      zIndex={9}>
      <Box
        bg={{base: 'blue.500'}}
        borderRadius={15}
        m={{base: 3}}
        p={{base: 2}}
        display={{base: 'flex'}}
        alignItems={{base: 'center'}}>
        <Image
          src={cdnImageLoader({
            src:
              station.now_playing?.song?.thumbnail_url ||
              station.thumbnail_url ||
              CONSTANTS.DEFAULT_COVER,
            width: 384,
            quality: 80,
          })}
          fallbackSrc={station.thumbnail_url || CONSTANTS.DEFAULT_COVER}
          alt={station.title}
          boxSize={{base: '70px'}}
          htmlHeight={80}
          htmlWidth={80}
          borderRadius={{base: '12px'}}
          style={{filter: 'drop-shadow(2px 2px 5px rgba(0, 0, 0, 0.25))'}}
          loading={'eager'}
          objectFit={'cover'}
        />
        <Flex
          w={'100%'}
          mt={{base: 0}}
          ml={{base: 4}}
          flexDirection={{base: 'row'}}>
          <Box>
            <Text
              as="h2"
              fontSize={{base: 'sm'}}
              mt={{base: 0}}
              lineHeight={1.3}
              color={{base: 'white'}}
              noOfLines={2}
              fontWeight="700">
              {station.now_playing?.song?.name || (
                <Box display={{base: 'block'}}>{station.title}</Box>
              )}
            </Text>
            <Text
              as="h3"
              fontSize={{base: 'sm'}}
              color={{base: 'white'}}
              noOfLines={1}>
              {station.now_playing?.song?.artist.name}
            </Text>
          </Box>
          <Spacer />
          <Flex
            w={{base: 'fit-content'}}
            mt={{base: 0}}
            ml={{base: 6}}
            mr={{base: 5}}
            alignItems="center">
            <button
              name="Start/Stop"
              onClick={() => {
                setPlaying(!isPlaying);
              }}>
              <Box fill={{base: 'white'}}>
                <svg
                  width="50px"
                  height="50px"
                  focusable="false"
                  aria-hidden="true"
                  viewBox="0 0 24 24">
                  {isPlaying ? (
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z"></path>
                  ) : (
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zM9.5 16.5v-9l7 4.5-7 4.5z"></path>
                  )}
                </svg>
              </Box>
            </button>
            <Box ml={{base: 4}} display={{base: 'none'}} alignItems="center">
              <Slider
                w={{base: '120px'}}
                aria-label="Volume"
                defaultValue={volume}
                onChange={value => {
                  setVolume(value as number);
                }}>
                <SliderTrack bg={{base: 'gray.400'}}>
                  <SliderFilledTrack bg={{base: 'white'}} />
                </SliderTrack>
                <SliderThumb boxSize={6} />
              </Slider>
            </Box>
            <Box>
              <ReactPlayer
                url={station_url}
                width={0}
                height={0}
                playing={isPlaying}
                muted={isMuted}
                volume={volume / 100}
                onPlay={() => {
                  console.debug('onPlay');
                  setMuted(false);
                  setPlaying(true);
                }}
                onPause={() => {
                  console.debug('pause');
                  setMuted(true);
                }}
                onReady={r => {
                  console.debug('ready');
                }}
                onEnded={() => {
                  console.debug('onEnded');
                }}
                onError={e => {
                  console.error(e);
                  if (!retryMechanism()) {
                    setPlaying(false);
                  }
                }}
                config={{
                  file: {
                    attributes: {
                      autoPlay:
                        (isMobile && hasInteracted && isPlaying) ||
                        (isDesktop && isPlaying),
                    },
                    forceAudio: true,
                  },
                }}
              />
            </Box>
          </Flex>
        </Flex>
      </Box>
    </Box>
  );
}
