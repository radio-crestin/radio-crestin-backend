import {capitalize} from '@/utils/capitalize';

export const seoStation = (
  stationTitle: string,
  stationDescription: string | null,
) => {
  return {
    title: `${stationTitle + ' · LIVE  ·'} Radio Crestin `,
    description: `${stationTitle} · 📻 ${
      stationDescription ||
      `Asculta ${stationTitle} live · Lista de radiouri crestine · Radio Crestin Live`
    }`,
    keywords: `${stationTitle}, ${stationTitle} live, ${stationTitle} online, radio crestin, radio-crestin.com, radiouri crestine romanesti, radio crestin online, muzica crestina, lista radio crestin, radio fm crestin`,
  };
};

export const seoCategory = (category: string) => {
  return {
    title: `Radiouri crestine · ${capitalize(category)}`,
    description: `Asculta radio crestin online 📻 · ${capitalize(category)}`,
    keywords: `post radio crestin, radio ${category} live,  radio-crestin.com, radio crestin online, muzica crestina, lista radio crestin, radio fm crestin, lista radio crestin online, radio crestin muzica non stop`,
  };
};

export const seoHomepage = {
  title: `Radio Crestin · Asculta Radio Crestin online`,
  description: `Radio-Crestin.com contine o lista cu cele mai populare radiouri crestine din Romania, dar si din strainatate. Aici vei gasi radiouri crestine FM, dar si din online. Te invitam sa asculti impreuna cu noi radio crestin online.`,
  keywords: `radio crestin, radiouri crestine, radio-crestin.com, radio crestin online, cantari crestine, muzica crestina, lista radio crestin, radio fm crestin, radiouri crestine romanesti`,
};

export const seoNotFoundPage = {
  title: `Stația nu a fost găsită`,
};

export const seoInternalErrorPage = {
  title: `A apărut o eroare neașteptată`,
};

export const seoPrivacyPolicy = {
  title: `Politica de confidențialitate`,
  description: `Politica de confidențialitate a site-ului Radio-Crestin.com`,
  keywords: ``,
};
