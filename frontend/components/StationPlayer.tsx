import React, {useEffect, useState} from 'react';
import {useRouter} from 'next/router';
import {isIOS, isMobile} from 'react-device-detect';
import dynamic from 'next/dynamic';
import {
  Box,
  Flex,
  Slider,
  SliderFilledTrack,
  SliderThumb,
  SliderTrack,
  Spacer,
  Text,
} from '@chakra-ui/react';

import {useTimeoutFn} from 'react-use';
import {useLocalStorageState} from '@/utils/state';
import {trackListenClientSide} from '../frontendServices/listen';
import {CONSTANTS} from '../lib/constants';
import {Station} from '../types';
import {Loading} from '@/public/images/loading';
import {
  ImageWithFallback
} from '@/components/ImageWithFallback/ImageWithFallback';
import canAutoplay from 'can-autoplay';

const ReactPlayer = dynamic(() => import('react-player/lazy'), {ssr: false});

enum STREAM_TYPE {
  HLS = 'HLS',
  PROXY = 'PROXY',
  ORIGINAL = 'ORIGINAL',
}

const STREAM_TYPE_INFO: any = {
  [STREAM_TYPE.HLS]: {
    field: 'hls_stream_url',
    name: 'hls',
  },
  [STREAM_TYPE.PROXY]: {
    field: 'proxy_stream_url',
    name: 'proxy',
  },
  [STREAM_TYPE.ORIGINAL]: {
    field: 'stream_url',
    name: 'original',
  },
};
const MAX_MEDIA_RETRIES = 20;

enum PLAYBACK_STATE {
  STARTED = 'started',
  STOPPED = 'stopped',
  PAUSED = 'paused',
  BUFFERING = 'buffering',
  PLAYING = 'playing',
  ERROR = 'error',
}

export default function StationPlayer({stations}: any) {
  const router = useRouter();
  const {station_slug} = router.query;
  const [retries, setRetries] = useState(MAX_MEDIA_RETRIES);
  const [playbackState, setPlaybackState] = useState(PLAYBACK_STATE.STOPPED);
  const [volume, setVolume] = useLocalStorageState(60, 'AUDIO_PLAYER_VOLUME');
  const [streamType, setStreamType] = useState(STREAM_TYPE.HLS);

  const [canAutoplayV, setcanAutoplayV] = useState(false);

  const [, cancelPlayerTimeout, resetPlayerTimeout] = useTimeoutFn(async () => {
    if ((playbackState === PLAYBACK_STATE.STARTED || playbackState === PLAYBACK_STATE.BUFFERING)) {
      console.log("start timed out after 5 seconds, calling the retrying mechanism...", {playbackState});
      if (!await retryMechanism()) {
        setPlaybackState(PLAYBACK_STATE.ERROR)
      }
    }
  }, 5000);
  cancelPlayerTimeout();

  useEffect(() => {
    if (playbackState === PLAYBACK_STATE.STARTED) {
      resetPlayerTimeout();
    }
  }, [station_slug, playbackState])

  console.debug({station_slug, streamType, playbackState})

  useEffect(() => {
    canAutoplay.audio().then(({result}) => {
      setcanAutoplayV(result);
    })
  }, [])

  useEffect(() => {
    setStreamType(STREAM_TYPE.HLS);
  }, [station_slug])

  useEffect(() => {
    if (isMobile && !canAutoplayV) {
      setPlaybackState(PLAYBACK_STATE.STOPPED);
    }
  }, []);

  const station: Station = stations.find(
    (station: { slug: string }) => station.slug === station_slug,
  );

  if (!station) {
    return <></>;
  }

  const nextRandomStation = () => {
    const randomStation = stations[Math.floor(Math.random() * stations.length)];
    router.push(`/radio/${randomStation.slug}`);
  }

  // TODO: we might need to populate these from local storage
  const retryMechanism = async () => {
    console.debug('retryMechanism called', {streamType});
    setRetries(retries - 1);
    console.debug('remaining retries: ', retries);
    if (retries > 0) {
      await new Promise(r => setTimeout(r, 200));

      if (streamType === STREAM_TYPE.HLS) {
        console.debug('waiting 1s before changing to PROXY');
        await new Promise(r => setTimeout(r, 1000));
        setStreamType(STREAM_TYPE.PROXY);
        return true;
      }
      if (streamType === STREAM_TYPE.PROXY) {
        console.debug('waiting 1s before changing to ORIGINAL');
        await new Promise(r => setTimeout(r, 1000));
        setStreamType(STREAM_TYPE.ORIGINAL);
        return true;
      }
      if (streamType === STREAM_TYPE.ORIGINAL) {
        console.debug('waiting 1s before changing to HLS');
        await new Promise(r => setTimeout(r, 1000));
        setStreamType(STREAM_TYPE.HLS);
        return true;
      }
    }
    return false;
  };

  // @ts-ignore
  const station_url = streamType === null ? null : station[STREAM_TYPE_INFO[streamType].field];

  useEffect(() => {
    if ('mediaSession' in navigator) {
      if (playbackState === PLAYBACK_STATE.PLAYING) {
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

  const actionHandlers = [
    ['pause', () => {
      console.debug("notification pause");
      setPlaybackState(PLAYBACK_STATE.PAUSED);
    }],
    ['stop', () => {
      console.debug("notification stop");
      setPlaybackState(PLAYBACK_STATE.STOPPED);
    }],
    ['nexttrack', () => {
      console.debug("notification nexttrack");
      nextRandomStation();
    }],
  ];

  for (const [action, handler] of actionHandlers) {
    try {
      // @ts-ignore
      navigator.mediaSession.setActionHandler(action, handler);
    } catch (error) {
      console.log(`The media session action "${action}" is not supported yet.`);
    }
  }

  // TODO: when the user click play, increase the number of listeners by 1
  // Also, delay the updated by 500 ms, also optional we can add an animation when we update the listeners counter.. to emphasis it
  // TODO: make the player mobile responsive

  useEffect(() => {
    if (playbackState === PLAYBACK_STATE.PLAYING) {
      trackListenClientSide({
        station_id: station.id as unknown as bigint,
        info: {},
      });
    }
    const timer = setInterval(() => {
      if (playbackState === PLAYBACK_STATE.PLAYING) {
        trackListenClientSide({
          station_id: station.id as unknown as bigint,
          info: {},
        });
      }
    }, 30 * 1000);
    return () => clearInterval(timer);
  }, [playbackState]);

  const renderPlayButtonSvg = () => {
    switch (playbackState) {
      case PLAYBACK_STATE.STARTED:
        return <Loading/>;
      case PLAYBACK_STATE.BUFFERING:
        return <Loading/>;
      case PLAYBACK_STATE.PLAYING:
        return <path
          d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z"/>;
      default:
        return <path
          d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zM9.5 16.5v-9l7 4.5-7 4.5z"/>;
    }
  }

  const playbackEnabled = playbackState === PLAYBACK_STATE.STARTED || playbackState === PLAYBACK_STATE.PLAYING || playbackState === PLAYBACK_STATE.BUFFERING;

  return (
    <Box
      w={{base: '100%'}}
      h={{base: 'auto'}}
      minW={{base: 'auto'}}
      maxW={'560px'}
      pl={{base: 0}}
      position="fixed"
      bottom={0}
      right={0}
      left={0}
      margin="auto"
      zIndex={9}>
      <Box
        bg={{base: 'black'}}
        boxShadow={'0 10px 30px 0 rgb(0 0 0 / 15%)'}
        borderRadius={16}
        m={{base: 3}}
        p={{base: 2}}
        display={{base: 'flex'}}
        alignItems={{base: 'center'}}>
        <ImageWithFallback
          src={
            station.now_playing?.song?.thumbnail_url ||
            station.thumbnail_url ||
            CONSTANTS.DEFAULT_COVER
          }
          fallbackSrc={station.thumbnail_url || CONSTANTS.DEFAULT_COVER}
          alt={`${station.title} | Radio Crestin`}
          htmlHeight={80}
          htmlWidth={80}
          loading={'eager'}
          borderRadius={{base: '12px'}}
          style={{
            filter: station?.uptime?.is_up ? 'unset' : 'grayscale(1)',
            objectFit: 'cover',
            width: '80px',
            height: '80px',
          }}
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
          <Spacer marginLeft={2}/>
          <Box
            ml={{base: 4}}
            margin={'auto'}
            display={{base: 'none', md: 'block'}}>
            <Slider
              w={{base: '100px'}}
              marginTop={2}
              aria-label="Volume"
              defaultValue={volume}
              step={0.5}
              onChange={value => {
                setVolume(value as number);
              }}>
              <SliderTrack bg={{base: 'gray.400'}}>
                <SliderFilledTrack bg={{base: 'white'}}/>
              </SliderTrack>
              <SliderThumb boxSize={5}/>
            </Slider>
          </Box>
          <Flex
            w={{base: 'fit-content'}}
            mt={{base: 0}}
            ml={{base: 3, md: 6}}
            mr={{base: 2, md: 5}}
            alignItems="center">
            <button
              name="Start/Stop"
              onClick={() => {
                setPlaybackState(
                  playbackState === PLAYBACK_STATE.PLAYING || playbackState === PLAYBACK_STATE.STARTED
                    ? PLAYBACK_STATE.STOPPED
                    : PLAYBACK_STATE.STARTED,
                );
              }}>
              <Box fill={{base: 'white'}}>
                <svg
                  width="50px"
                  height="50px"
                  focusable="false"
                  aria-hidden="true"
                  viewBox="0 0 24 24">
                  {renderPlayButtonSvg()}
                </svg>
              </Box>
            </button>
            <Box>
              {/* it seems that on IOS, we are not allowed to change the audio url after interaction */}
              <ReactPlayer
                url={playbackEnabled && station_url || 'data:audio/mpeg;base64,SUQzBAAAAAABEVRYWFgAAAAtAAADY29tbWVudABCaWdTb3VuZEJhbmsuY29tIC8gTGFTb25vdGhlcXVlLm9yZwBURU5DAAAAHQAAA1N3aXRjaCBQbHVzIMKpIE5DSCBTb2Z0d2FyZQBUSVQyAAAABgAAAzIyMzUAVFNTRQAAAA8AAANMYXZmNTcuODMuMTAwAAAAAAAAAAAAAAD/80DEAAAAA0gAAAAATEFNRTMuMTAwVVVVVVVVVVVVVUxBTUUzLjEwMFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVf/zQsRbAAADSAAAAABVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVf/zQMSkAAADSAAAAABVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV'}
                width={0}
                height={0}
                playing={playbackEnabled}
                volume={volume / 200}
                playsinline={true}
                disabledeferredloading={"true"}
                onBuffer={() => {
                  console.debug('onBuffer');
                  setPlaybackState(PLAYBACK_STATE.BUFFERING);
                }}
                onBufferEnd={() => {
                  console.debug('onBufferEnd');
                  setPlaybackState(PLAYBACK_STATE.PLAYING);
                }}
                onPlay={() => {
                  console.debug('onPlay');
                }}
                onPause={() => {
                  console.debug('onPause');
                }}
                onStart={() => {
                  console.debug('onStart');
                  setPlaybackState(PLAYBACK_STATE.STARTED);
                }}
                onReady={r => {
                  console.debug('onReady');
                }}
                onEnded={() => {
                  console.debug('onEnded');
                }}
                onError={async (error, ...args) => {
                  if (error?.target?.error?.code === 4) {
                    // Ignore this error as we know that we've passed an empty src attribute
                    console.debug("Ignoring error: ", error?.target?.error, error, args);
                    return;
                  }
                  console.trace('player onError:', error, args);
                  if (!await retryMechanism()) {
                    setPlaybackState(PLAYBACK_STATE.ERROR)
                  }
                }}
                config={{
                  file: {
                    attributes: {
                      autoPlay: canAutoplayV && playbackEnabled,
                      preload: 'none',
                    },
                    forceAudio: isIOS ? true : playbackEnabled && streamType !== STREAM_TYPE.HLS,
                    forceHLS: isIOS ? false : playbackEnabled && streamType === STREAM_TYPE.HLS
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
