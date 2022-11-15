import React, {useEffect, useMemo, useState} from 'react';
import {Station} from '../../types';
import {CONSTANTS} from '../../lib/constants';
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
import NoSSR from 'react-no-ssr';
import {trackListenClientSide} from '../../frontendServices/listen';
import dynamic from 'next/dynamic';
import {cdnImageLoader} from '@/utils/cdnImageLoader';

let firstStart = true;
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

const DynamicReactPlayer = dynamic(() => import('react-player'), {ssr: false});

export default function StationPlayer(props: {station: Station}) {
  const {station} = props;

  const [retries, setRetries] = useState(MAX_MEDIA_RETRIES);

  const [playing, setPlayingOriginalMethod] = useLocalStorageState(
    false,
    'IS_PLAYING',
  );
  const [frontendPlaying, setFrontendPlaying] = useState(false);
  const setPlaying = (newPlayingState: boolean) => {
    setPlayingOriginalMethod(newPlayingState);
    setFrontendPlaying(newPlayingState);
  };
  firstStart = false;

  // TODO: we might need to populate these from local storage
  const [volume, setVolume] = useLocalStorageState(60, 'AUDIO_PLAYER_VOLUME');

  const [selectedStreamType, setSelectedStreamType] = useState('HLS');

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
      if (playing) {
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

  const floatingPlayer = true;

  useEffect(() => {
    if (playing) {
      trackListenClientSide({
        station_id: station.id as unknown as bigint,
        info: {},
      });
    }
    const timer = setInterval(() => {
      if (playing) {
        trackListenClientSide({
          station_id: station.id as unknown as bigint,
          info: {},
        });
      }
    }, 30 * 1000);
    return () => clearInterval(timer);
  });

  return (
    <Box
      w={{base: '100%', lg: '29%'}}
      h={{base: 'auto', lg: '360px'}}
      minW={{base: 'auto', lg: '250px'}}
      maxW={'100%'}
      pl={{base: 0, lg: 4}}
      position={{base: 'fixed', lg: 'relative'}}
      bottom={{base: '0', lg: 'auto'}}
      left={{base: '0', lg: 'auto'}}
      right={{base: '0', lg: 'auto'}}
      zIndex={9}>
      <Box
        bg={{base: 'blue.500', lg: 'transparent'}}
        borderRadius={15}
        m={{base: 3, lg: 0}}
        p={{base: 2, lg: 0}}
        display={{base: 'flex', lg: 'block'}}
        alignItems={{base: 'center', lg: 'auto'}}>
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
          boxSize={{base: '70px', lg: '220px'}}
          htmlHeight={250}
          htmlWidth={250}
          borderRadius={{base: '12px', lg: '30px'}}
          style={{filter: 'drop-shadow(2px 2px 5px rgba(0, 0, 0, 0.25))'}}
          loading={'eager'}
        />
        <Flex
          w={'100%'}
          mt={{base: 0, lg: 3}}
          ml={{base: 4, lg: 0}}
          flexDirection={{base: 'row', lg: 'column'}}>
          <Box>
            <Text
              as="h2"
              fontSize={{base: 'sm', lg: '2xl'}}
              mt={{base: 0, lg: 2}}
              lineHeight={1.3}
              color={{base: 'white', lg: 'gray.800'}}
              noOfLines={2}
              fontWeight="700">
              {station.now_playing?.song?.name || (
                <Box display={{base: 'block', lg: 'none'}}>{station.title}</Box>
              )}
            </Text>
            <Text
              as="h3"
              fontSize={{base: 'sm', lg: 'lg'}}
              color={{base: 'white', lg: 'gray.800'}}
              noOfLines={1}>
              {station.now_playing?.song?.artist.name}
            </Text>
          </Box>
          <Spacer />
          <Flex
            w={{base: 'fit-content', lg: '100%'}}
            mt={{base: 0, lg: 4}}
            ml={{base: 6, lg: 0}}
            mr={{base: 5, lg: 0}}
            alignItems="center">
            <button
              name="Start/Stop"
              onClick={() => {
                setPlaying(!playing);
              }}>
              <Box fill={{base: 'white', lg: 'gray.900'}}>
                <svg
                  width="50px"
                  height="50px"
                  focusable="false"
                  aria-hidden="true"
                  viewBox="0 0 24 24">
                  {frontendPlaying ? (
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z"></path>
                  ) : (
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zM9.5 16.5v-9l7 4.5-7 4.5z"></path>
                  )}
                </svg>
              </Box>
            </button>
            <Box
              ml={{base: 4, lg: 5}}
              display={{base: 'none', lg: 'flex'}}
              alignItems="center">
              <Slider
                w={{base: '120px', lg: '175px'}}
                aria-label="Volume"
                defaultValue={volume}
                onChange={value => {
                  setVolume(value as number);
                }}>
                <SliderTrack bg={{base: 'gray.400', lg: 'gray.200'}}>
                  <NoSSR>
                    <SliderFilledTrack bg={{base: 'white', lg: 'gray.900'}} />
                  </NoSSR>
                </SliderTrack>
                <SliderThumb boxSize={6} />
              </Slider>
            </Box>
            <Box>
              {useMemo(() => {
                return (
                  <DynamicReactPlayer
                    url={playing ? station_url : ''}
                    width={0}
                    height={0}
                    playing={playing}
                    // controls={true}
                    volume={volume / 100}
                    onPlay={() => {
                      console.debug('onPlay');
                      setFrontendPlaying(true);
                    }}
                    onPause={() => {
                      console.debug('pause');
                      setFrontendPlaying(false);
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
                          autoPlay: false,
                        },
                        forceAudio: true,
                      },
                    }}
                  />
                );
              }, [station_url, playing, volume])}
            </Box>
          </Flex>
        </Flex>
      </Box>
    </Box>
  );
}
