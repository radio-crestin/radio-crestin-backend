import dynamic from "next/dynamic";
import {isMobile} from "react-device-detect";

export const ContactButton = dynamic(
  () => (isMobile ? import("./WhatsAppButton") : import("./EmailButton")),
  {ssr: false}
);
