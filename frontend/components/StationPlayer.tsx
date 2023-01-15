import React, {useEffect, useState} from 'react';
import {useRouter} from 'next/router';
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
import {useLocalStorageState} from '@/utils/state';
import {trackListenClientSide} from '../frontendServices/listen';
import {CONSTANTS} from '../lib/constants';
import {Loading} from '@/public/images/loading';
import {ImageWithFallback} from '@/components/ImageWithFallback/ImageWithFallback';
import Hls from 'hls.js';

enum STREAM_TYPE {
  HLS = 'HLS',
  PROXY = 'PROXY',
  ORIGINAL = 'ORIGINAL',
}

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

  // const [, cancelPlayerTimeout, resetPlayerTimeout] = useTimeoutFn(async () => {
  //   if (
  //     playbackState === PLAYBACK_STATE.STARTED ||
  //     playbackState === PLAYBACK_STATE.BUFFERING
  //   ) {
  //     console.log(
  //       'start timed out after 5 seconds, calling the retrying mechanism...',
  //       {playbackState},
  //     );
  //     if (!(await retryMechanism())) {
  //       setPlaybackState(PLAYBACK_STATE.ERROR);
  //     }
  //   }
  // }, 5000);
  // cancelPlayerTimeout();

  // TODO: Check if is still needed ("To not make useless requests to BunnyCDN")
  // useEffect(() => {
  //   if (playbackState === PLAYBACK_STATE.STARTED) {
  //     resetPlayerTimeout();
  //   }
  // }, [station_slug, playbackState]);

  console.debug({station_slug, streamType, playbackState});

  const station = stations.find(
    (station: {slug: string}) => station.slug === station_slug,
  );

  if (!station) {
    return <></>;
  }

  useEffect(() => {
    const audio = document.getElementById('audioPlayer') as HTMLAudioElement;
    let hls: Hls = new Hls();

    if (Hls.isSupported()) {
      hls.loadSource(station.hls_stream_url);
      hls.attachMedia(audio);
      hls.on(Hls.Events.ERROR, function (event, data) {
        if (data.fatal) {
          retryMechanism();
        }
      });
    }

    return () => {
      hls.destroy();
      setStreamType(STREAM_TYPE.HLS);
      setRetries(20);
    };
  }, [station.slug]);

  const retryMechanism = () => {
    const audio = document.getElementById('audioPlayer') as HTMLAudioElement;
    console.log('before audio.src: ', audio.src, Date.now());
    setRetries(retries - 1);
    if (retries > 0) {
      switch (streamType) {
        case STREAM_TYPE.HLS:
          setStreamType(STREAM_TYPE.PROXY);
          audio.src = station.proxy_stream_url;
          break;
        case STREAM_TYPE.PROXY:
          setStreamType(STREAM_TYPE.ORIGINAL);
          audio.src = station.stream_url;
          break;
      }
    }
    console.log('after audio.src: ', audio.src, Date.now());
  };

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
        return <Loading />;
      case PLAYBACK_STATE.BUFFERING:
        return <Loading />;
      case PLAYBACK_STATE.PLAYING:
        return (
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z" />
        );
      default:
        return (
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zM9.5 16.5v-9l7 4.5-7 4.5z" />
        );
    }
  };

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
          <Spacer marginLeft={2} />
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
                <SliderFilledTrack bg={{base: 'white'}} />
              </SliderTrack>
              <SliderThumb boxSize={5} />
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
                  playbackState === PLAYBACK_STATE.PLAYING ||
                    playbackState === PLAYBACK_STATE.STARTED
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
            <audio
              preload="true"
              controls
              autoPlay
              id="audioPlayer"
              onError={() => {
                retryMechanism();
              }}
            />
          </Flex>
        </Flex>
      </Box>
    </Box>
  );
}
