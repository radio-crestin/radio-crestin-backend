import React from "react";

export default function Analytics(props: { children?: any }) {
  return (
    <>
      {props.children}

      {/*TODO: Add this after merge*/}
      {/*<script defer src='https://static.cloudflareinsights.com/beacon.min.js'*/}
      {/*        data-cf-beacon='{"token": "c2153a600cc94f69848e4decff1983a1"}'/>*/}
      <script
        async
        src="https://www.googletagmanager.com/gtag/js?id=UA-204935415-1"></script>
      <script src="/ga.js" async></script>
      <script src="/hj.js" async></script>
    </>
  );
}
