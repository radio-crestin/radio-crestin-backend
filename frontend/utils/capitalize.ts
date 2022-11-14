/**
 * Make the first letter of a string uppercase
 *
 * @param str - string
 * @returns a string
 */

export const capitalize = (str: string) => {
  return str[0].toUpperCase() + str.slice(1);
};
