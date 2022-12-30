import {capitalize} from '@/utils/capitalize';

export const seoStation = (
  stationTitle: string,
  stationDescription: string | null,
  extraKeywords?: string,
) => {
  return {
    title: `${stationTitle + ' · LIVE  ·'} Radio Crestin `,
    description: `${stationTitle} · 📻 ${
      stationDescription ||
      `Asculta ${stationTitle} live · Lista de radiouri crestine · Radio Crestin Live`
    }`,
    keywords: `${stationTitle}, asculta ${stationTitle} live, post radio, live, radio crestin online, cantari, crestine, radiouri, muzica crestina, lista radio crestin, asculta radio crestin online, radio fm crestine, lista radio crestin online, \t
  radio crestin muzica non stop,  radio-crestin.com, ${extraKeywords}`,
  };
};

export const seoCategory = (category: string) => {
  return {
    title: `Radiouri crestine · ${capitalize(category)}`,
    description: `Asculta radio crestin online 📻 · ${capitalize(category)}`,
    keywords: `post radio, radio ${category} live, radio crestin online, cantari, crestine, radiouri, muzica crestina, lista radio crestin, asculta radio crestin online, radio fm crestine, lista radio crestin online,
  radio crestin muzica non stop, radio-crestin.com`,
  };
};

export const seoHomepage = {
  title: `Radio Crestin · Asculta Radio Crestin online`,
  description: `Radio-Crestin.com contine o lista cu cele mai populare radiouri crestine din Romania, dar si din strainatate. Aici vei gasi radiouri crestine FM, dar si din online. Te invitam sa asculti impreuna cu noi radio crestin online.`,
  keywords: `post radio, live, radio crestin online, cantari, crestine, radiouri, muzica crestina, lista radio crestin, asculta radio crestin online, radio fm crestine, lista radio crestin online,
  radio crestin muzica non stop, radio-crestin.com`,
};

export const seoNotFoundPage = {
  title: `Stația nu a fost găsită`,
};

export const seoInternalErrorPage = {
  title: `A apărut o eroare neașteptată`,
};
