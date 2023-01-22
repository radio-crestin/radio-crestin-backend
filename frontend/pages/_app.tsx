import 'styles/globals.scss'
import type {AppProps} from 'next/app'
import {ChakraProvider, extendTheme} from "@chakra-ui/react";


// 2. Extend the theme to include custom colors, fonts, etc
const colors = {
  brand: {
    900: '#ee8614',
    800: '#fda446',
    700: '#ffb05a',
    600: '#ffd9af',
  },
}

const theme = extendTheme({colors})

function MyApp({Component, pageProps}: AppProps) {
  return <ChakraProvider theme={theme}>
    <Component {...pageProps} />
  </ChakraProvider>
}

export default MyApp

