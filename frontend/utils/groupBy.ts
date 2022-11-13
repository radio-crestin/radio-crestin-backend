export const groupBy = function (xs: any[], key: string) {
  return xs.reduce(function (rv, x) {
    rv[x[key]] = x;
    return rv;
  }, {});
};
