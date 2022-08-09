// v1.3
self.addEventListener('install', function(event) {
});

// const fetchRequestAndCache = (cache, request, importance ) => {
//   return fetch(request, { importance: importance || "high" }).then(response => {
//     console.log("The cache has been updated: ", response);
//     cache.put(request, response.clone());
//     return response;
//   });
// };
//
// self.addEventListener('fetch', (event) => {
//   event.respondWith(async function() {
//     if(event.request.method === "GET" && event.request.url.startsWith("https://cdn.") && !event.request.url.includes("hls")) {
//       const cache = await caches.open('radio-crestin-dynamic');
//       const cachedResponse = await cache.match(event.request);
//       if (cachedResponse) {
//         fetchRequestAndCache(cache, event.request, "low");
//         return cachedResponse;
//       } else {
//         console.log("Waiting for network");
//         return await fetchRequestAndCache(cache, event.request, "high");
//       }
//     } else {
//       return await fetch(event.request, { importance: "high" });
//     }
//   }());
// });
