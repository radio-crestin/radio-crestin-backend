import {useEffect, useState} from "react";

export const useLocalStorageState = function (defaultValue: any, key: any) {
  const [value, setValue] = useState(() => {
    const stickyValue = typeof window !== "undefined" ? window.localStorage.getItem(key) : null;
    return stickyValue !== null
      ? JSON.parse(stickyValue)
      : defaultValue;
  });
  useEffect(() => {
    const stickyValue = typeof window !== "undefined" ? window.localStorage.getItem(key) : null;
    if (stickyValue !== null) {
      setValue(JSON.parse(stickyValue));
    }
  }, [key, setValue]);

  useEffect(() => {
    window.localStorage.setItem(key, JSON.stringify(value));
  }, [key, value]);
  return [value, setValue];
}
