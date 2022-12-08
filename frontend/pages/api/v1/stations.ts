import {getStationsMetadata} from '../../../backendServices/stations';
import {NextApiRequest, NextApiResponse} from 'next';
import {StationsMetadata} from '../../../types';

export default function handler(
  req: NextApiRequest,
  res: NextApiResponse<StationsMetadata>,
) {
  res.setHeader(
    'Cache-Control',
    'public, s-maxage=1, stale-while-revalidate=5',
  );
  return getStationsMetadata().then(stationsMetadata => {
    res.status(200).json(stationsMetadata);
  });
}
