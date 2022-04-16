import {PROJECT_ENV} from "../utils/env";

export const ironOptions = {
  cookieName: "session",
  password: PROJECT_ENV.FRONTEND_COOKIE_SECRET,
  cookieOptions: {
    secure: process.env.NODE_ENV === "production",
  },
};
