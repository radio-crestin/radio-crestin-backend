module.exports = {
  content: [
    "../../**/*.{html,py,js}",
    "./node_modules/flowbite/**/*.js"
  ],
  media: false,
  darkMode: "class",
  theme: {
    extend: {
      fontSize: {
        0: [0, 1],
        xxs: ["11px", "14px"],
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
      },
      height: {
        9.5: "2.375rem",
      },
      minWidth: {
        sidebar: "18rem",
      },
      spacing: {
        68: "17rem",
        128: "32rem",
      },
      transitionProperty: {
        height: "height",
        width: "width",
      },
      width: {
        4.5: "1.125rem",
        9.5: "2.375rem",
        sidebar: "18rem",
      },
      colors: {
        custom: {
          scrollbarDarkColor: '#576481',
          scrollbarColor: '#0000003b',
          transparent: '#00000000',
        },
      },
      keyframes: {
        "caret-blink": {
          "0%,70%,100%": { opacity: "1" },
          "20%,50%": { opacity: "0" },
        },
      },
      animation: {
        "caret-blink": "caret-blink 1.25s ease-out infinite",
      },
    },
  },
  variants: {
    extend: {
      backgroundColor: ['hover'],
      borderColor: ["checked", "focus-within", "hover"],
      display: ["group-hover"],
      overflow: ["hover"],
      textColor: ["hover"],
    },
  },
  plugins: [
      require("@tailwindcss/typography"),
      require('flowbite/plugin')({
        charts: true,
      }),
      require('tailwind-scrollbar'),
    ],
  safelist: [
    "md:border-0",
    "md:border-r",
    "md:w-48",
    {
      pattern: /gap-+/,
      variants: ["lg"],
    },
    {
      pattern: /w-(1\/2|1\/3|2\/3|1\/4|2\/4|3\/4|1\/5|2\/5|3\/5|4\/5)/,
      variants: ["lg"],
    },
  ],
};

