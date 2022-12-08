/**
 * Given a list and a key, returns an object with an index of each item
 *
 * @param xs - array
 * @param key - string
 *
 * @returns an object
 */

export const indexBy = function (xs: any[], key: string) {
  return xs.reduce(function (rv, x) {
    rv[x[key]] = x;
    return rv;
  }, {});
};
