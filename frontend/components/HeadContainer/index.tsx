import React from 'react';
import Head from 'next/head';

export default function HeadContainer({selectedStation, seo, fullURL}: any) {
  return (
    <Head>
      <title>{seo.title}</title>
      <link
        rel="image_src"
        href={
          selectedStation?.thumbnail_url || '/images/android-chrome-512x512.png'
        }
      />
      <meta name="viewport" content="initial-scale=1.0, width=device-width" />
      <meta property="title" content={seo?.title} />
      <meta name="description" content={seo?.description} />
      <meta name="keywords" content={seo?.keywords} />
      <meta
        property="image:alt_text"
        content={`${
          selectedStation?.title || 'Asculta radio crestin online'
        } | Radio Crestin`}
      />
      <meta property="og:site_name" content="Radio Crestin" />
      <meta property="og:type" content="website" />
      <meta property="og:url" content={fullURL} />
      <meta property="og:title" content={seo?.title} />
      <meta property="og:description" content={seo?.description} />
      <meta
        property="og:image"
        content={
          selectedStation?.thumbnail_url || '/images/android-chrome-512x512.png'
        }
      />
      <meta
        property="og:image:url"
        content={
          selectedStation?.thumbnail_url || '/images/android-chrome-512x512.png'
        }
      />
      <meta
        property="og:image:secure_url"
        content={
          selectedStation?.thumbnail_url || '/images/android-chrome-512x512.png'
        }
      />
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:description" content={seo?.description} />
      <meta name="twitter:title" content={seo?.title} />
      <meta name="twitter:url" content={fullURL} />
      <meta
        name="twitter:image"
        content={
          selectedStation?.thumbnail_url || '/images/android-chrome-512x512.png'
        }
      />
      <meta name="MobileOptimized" content="width" />
      <meta name="HandheldFriendly" content="true" />
    </Head>
  );
}
